#!/usr/bin/env python3
"""
Server Sharing Identifier — Section 5 Algorithm (Single URL Setting)

In our setting, all scaled-out instances share the same public URL <url>. We cannot
directly choose which instance will handle a given request. Each instance exposes:

  <url>/lock         # triggers mem-lock on whichever instance handles this request
  <url>/check        # runs mem-check and returns memory access timing metrics
  <url>/instance_id  # returns a JSON object with a per-instance identifier

Algorithm (per Section 5):

  - Maintain a set of instances that have not yet been assigned to any group.
  - In each iteration:
      1. Call <url>/lock once.
      2. Immediately call <url>/instance_id to learn which instance actually
         performed mem-lock; denote this instance as I.
      3. If I has already been grouped, retry this iteration with another /lock.
      4. Otherwise, for all other (remaining) instances:
           * Issue multiple mem-check requests to <url>/check.
           * For each mem-check, record:
               - the internal mem-check metric (parsed from "count[k] is <value>")
               - the instance_id of the instance that handled /check
           * If an instance J's mem-check metric exceeds a threshold, J is inferred
             to share the same server as I.
      5. The server-sharing group for this iteration is:
             G = { I } ∪ { all J with mem-check metric >= THRESHOLD }
         Remove all instances in G from the remaining set.
  - Repeat until all instances are assigned to some group.

The concrete value of the threshold should be chosen empirically based on the mem-check distribution on a given platform.
"""

import re
import requests
import concurrent.futures
from typing import List, Dict, Any, Set

# ============================
# Configuration
# ============================

# All scaled-out instances share this public URL.
# Replace "https://<url>" with the actual service URL.
BASE_URL: str = "https://<url>"

LOCK_EP = "/lock"
CHECK_EP = "/check"
ID_EP = "/instance_id"

# Number of mem-check requests per iteration.
# This should be large enough to cover all remaining instances with high probability.
NUM_CHECK_REQUESTS: int = 60

# Per-request timeout (seconds)
REQUEST_TIMEOUT: float = 10.0

# Threshold on the mem-check metric (sum_count) for deciding server sharing.
# This script does NOT pick a concrete numeric value; set this in practice.
SERVER_SHARING_THRESHOLD = None  # e.g., 1e7, 5e7, etc., depending on platform


# ============================
# Helper functions
# ============================

def call_instance_id() -> str:
    """
    Call <url>/instance_id and return the instance_id string.
    """
    try:
        resp = requests.get(BASE_URL + ID_EP, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("instance_id", "unknown"))
    except requests.RequestException as e:
        print(f"[WARN] Failed to get instance_id: {e}")
        return "unknown"


def call_lock_and_get_instance_id() -> str:
    """
    Call <url>/lock once, then call <url>/instance_id to learn which instance
    actually handled the lock request.
    """
    try:
        requests.get(BASE_URL + LOCK_EP, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        print(f"[WARN] Failed to trigger lock: {e}")

    # Identify which instance handled the /lock request.
    lock_instance_id = call_instance_id()
    print(f"[INFO] /lock handled by instance_id={lock_instance_id}")
    return lock_instance_id


def call_check_and_get_metric_and_id() -> Dict[str, Any]:
    """
    Call <url>/check once and parse the internal mem-check metric from ./check output,
    then call <url>/instance_id to learn which instance handled /check.

    Returns:
      {
        "instance_id": <str>,
        "sum_count": <float>   # sum of count[k] values, or +inf on failure
      }
    """
    # 1. Call /check and capture its output
    try:
        resp = requests.get(BASE_URL + CHECK_EP, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        text = resp.text
    except requests.RequestException as e:
        print(f"[WARN] Failed to run mem-check: {e}")
        return {"instance_id": "unknown", "sum_count": float("inf")}

    # 2. Parse "count[k] is <value>" lines
    counts: List[int] = []
    for line in text.splitlines():
        m = re.search(r"count\[\d+\]\s+is\s+(\d+)", line)
        if m:
            counts.append(int(m.group(1)))

    if not counts:
        print("[WARN] No count[...] values parsed from /check output")
        sum_count = float("inf")
    else:
        sum_count = sum(counts)

    # 3. Identify which instance handled /check
    inst_id = call_instance_id()

    return {
        "instance_id": inst_id,
        "sum_count": sum_count,
    }


# ============================
# Main identification logic
# ============================

def identify_server_sharing(all_instance_ids: List[str]) -> List[List[str]]:
    """
    Perform the full multi-iteration server sharing identification.

    Args:
      all_instance_ids: list of all known instance IDs participating in the experiment.

    Returns:
      A list of groups, where each group is a list of instance_ids that share a server.
    """
    remaining: Set[str] = set(all_instance_ids)
    groups: List[List[str]] = []

    if SERVER_SHARING_THRESHOLD is None:
        print("[ERROR] SERVER_SHARING_THRESHOLD is not set.")
        print("        Set SERVER_SHARING_THRESHOLD to a positive float before running.")
        return groups

    print(f"[INFO] Starting server sharing identification.")
    print(f"[INFO] Total instances: {len(remaining)}")
    print(f"[INFO] Using SERVER_SHARING_THRESHOLD = {SERVER_SHARING_THRESHOLD}")

    while remaining:
        print(f"\n[INFO] Remaining instances: {len(remaining)}")
        # 1. Trigger mem-lock and see which instance actually handled it
        lock_instance_id = call_lock_and_get_instance_id()

        # If we failed to identify, retry
        if lock_instance_id == "unknown":
            print("[WARN] lock instance_id is unknown; retrying iteration.")
            continue

        # If this instance has already been grouped, skip and retry
        if lock_instance_id not in remaining:
            print(f"[INFO] lock instance_id {lock_instance_id} is already grouped; retrying.")
            continue

        print(f"[INFO] Using {lock_instance_id} as current lock instance.")

        # 2. Issue multiple mem-checks in parallel
        measurements: List[Dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CHECK_REQUESTS) as ex:
            futures = [ex.submit(call_check_and_get_metric_and_id) for _ in range(NUM_CHECK_REQUESTS)]
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                measurements.append(result)

        # 3. Build a metric map for instances that are still remaining
        #    (we keep the maximum sum_count observed per instance to reflect strongest slowdown)
        inst_metric: Dict[str, float] = {}
        for m in measurements:
            inst_id = m["instance_id"]
            sum_count = m["sum_count"]

            if inst_id not in remaining:
                continue
            if sum_count == float("inf"):
                continue

            if inst_id not in inst_metric:
                inst_metric[inst_id] = sum_count
            else:
                inst_metric[inst_id] = max(inst_metric[inst_id], sum_count)

        print("[DEBUG] Mem-check metrics for remaining instances:")
        for inst_id, metric in inst_metric.items():
            print(f"  instance_id={inst_id}, sum_count={metric}")

        # 4. Form server-sharing group: lock_instance + all instances with metric >= threshold
        group = {lock_instance_id}
        for inst_id, metric in inst_metric.items():
            if inst_id == lock_instance_id:
                continue
            if metric >= SERVER_SHARING_THRESHOLD:
                group.add(inst_id)

        group = list(group)
        print(f"[INFO] Identified server-sharing group: {group}")

        # 5. Remove grouped instances and record the group
        for gid in group:
            remaining.discard(gid)
        groups.append(group)

    return groups


# ============================
# Example usage
# ============================

def main():
    # In practice, this list should be populated by a separate discovery phase
    # that repeatedly calls /instance_id until all distinct instance_ids are found.
    all_instance_ids = [
        "instance-A",
        "instance-B",
        "instance-C",
        # ...
    ]

    groups = identify_server_sharing(all_instance_ids)

    print("\n[FINAL RESULT] Server sharing groups:")
    for idx, g in enumerate(groups, start=1):
        print(f"  Group {idx}: {g}")


if __name__ == "__main__":
    main()

