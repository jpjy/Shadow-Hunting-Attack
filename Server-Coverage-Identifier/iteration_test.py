#!/usr/bin/env python3
"""
Section 3.1 – Server Coverage Identifier 

Each attacker instance has a unique URL, and each URL exposes two endpoints:

  <url>/lock   # triggers mem-lock on that instance
  <url>/check  # runs mem-check and returns timing-related metrics (e.g., count[0])

Algorithm (per iteration):
  1. Select one instance URL L from the remaining set.
  2. Round 1:
       - Send /lock to L.
       - Send /check to all other remaining URLs concurrently.
       - Mark as candidates all URLs whose metric >= MEMCHECK_THRESHOLD.
  3. Round 2 (reverification):
       - Send /lock to L again.
       - Send /check only to the candidate URLs concurrently.
       - Keep only URLs that again have metric >= MEMCHECK_THRESHOLD.
  4. Group = { L } ∪ { verified URLs from Round 2 }.
  5. Remove all URLs in Group from the remaining set.
  6. Repeat until no URLs remain.

The script defines MEMCHECK_THRESHOLD but does NOT assign a concrete value.
"""

import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Set

# ============================
# Configuration
# ============================

# List of instance base URLs (each instance has its own URL).
# Replace with your actual URLs. Example:
INSTANCE_URLS: List[str] = [
    # "https://function-1.azurewebsites.net/api/",
    # "https://function-2.azurewebsites.net/api/",
    # ...
]

LOCK_ENDPOINT = "lock"
CHECK_ENDPOINT = "check"

REQUEST_TIMEOUT: float = 10.0

# Threshold on mem-check metric (e.g., count[0]) to decide server sharing.
# This script does NOT set a numeric value; choose empirically in practice.
# As attacker instances are controlled by the attacker, pre-observing the suitable memory access
# threshold is trivial.
MEMCHECK_THRESHOLD: Optional[int] = None  # e.g., 800, 1000 cpu cycles or 0.1 second, etc.


# ============================
# Helper functions
# ============================

def execute_endpoint(base_url: str, endpoint: str) -> str:
    """
    Execute base_url + endpoint and return the response text.
    base_url is something like 'https://.../api/'.
    endpoint is 'lock' or 'check'.
    """
    full_url = base_url + endpoint
    try:
        resp = requests.get(full_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[WARN] Request failed for {full_url}: {e}")
        return ""


def extract_count(response_text: str) -> Optional[int]:
    """
    Extract the mem-check metric from the response text.

    Here we use 'count[0] is <value>'.
    """
    m = re.search(r"count\[0\]\s+is\s+(\d+)", response_text)
    if not m:
        return None
    return int(m.group(1))


def run_iteration_for_lock(
    lock_url: str,
    check_urls: List[str],
) -> Dict[str, Optional[int]]:
    """
    Run a lock+check iteration for a given lock_url:

      1. Send /lock to lock_url.
      2. Send /check to all URLs in check_urls concurrently (one worker per URL).
      3. Return mapping: url -> count_value (or None if parsing failed).
    """
    print(f"\n[INFO] Starting lock+check iteration with lock_url={lock_url}")

    # 1. Trigger mem-lock on this instance
    _ = execute_endpoint(lock_url, LOCK_ENDPOINT)

    # Optional: small delay to ensure mem-lock effect is active
    time.sleep(0.1)

    results: Dict[str, Optional[int]] = {}

    if not check_urls:
        return results

    num_workers = len(check_urls)
    if num_workers <= 0:
        num_workers = 1

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_url = {
            executor.submit(execute_endpoint, url, CHECK_ENDPOINT): url
            for url in check_urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            resp_text = future.result()
            count_value = extract_count(resp_text)
            results[url] = count_value
            print(f"[DEBUG] {url}{CHECK_ENDPOINT}: count[0] = {count_value}")

    return results


# ============================
# Coverage identification logic
# ============================

def identify_server_coverage(instance_urls: List[str]):
    """
    Perform iterative server coverage identification over all instance_urls,
    with per-iteration reverification of group members.

    Returns:
      groups: a list of dicts:
        {
          "lock_url": <str>,
          "members": [list of URLs in this server-sharing group]
        }
    """
    if MEMCHECK_THRESHOLD is None:
        print("[ERROR] MEMCHECK_THRESHOLD is not set.")
        print("       Set MEMCHECK_THRESHOLD (e.g., 800) before running.")
        return []

    remaining: Set[str] = set(instance_urls)
    groups = []

    print(f"[INFO] Starting Server Coverage Identifier (with reverification).")
    print(f"[INFO] Total instances: {len(remaining)}")
    print(f"[INFO] MEMCHECK_THRESHOLD = {MEMCHECK_THRESHOLD}")

    while remaining:
        # 1. Select one URL from the remaining set as the lock instance
        lock_url = next(iter(remaining))
        print(f"\n[INFO] Remaining instances: {len(remaining)}")
        print(f"[INFO] Using lock_url={lock_url}")

        # The other URLs are probed via /check
        check_urls = [u for u in remaining if u != lock_url]

        if not check_urls:
            # Only one instance left; form a singleton group
            print("[INFO] Only one instance left; forming singleton group.")
            groups.append({"lock_url": lock_url, "members": [lock_url]})
            remaining.remove(lock_url)
            break

        # ---------- Round 1: initial grouping ----------
        check_results_round1 = run_iteration_for_lock(lock_url, check_urls)

        # Candidates: URLs above threshold in round 1
        candidate_urls = [
            url
            for url, count_value in check_results_round1.items()
            if count_value is not None and count_value >= MEMCHECK_THRESHOLD
        ]

        if not candidate_urls:
            # No one clearly shares this server; group is just the lock_url itself
            print("[INFO] No candidates exceeded threshold in Round 1.")
            group_members = [lock_url]
            groups.append({"lock_url": lock_url, "members": group_members})
            remaining.discard(lock_url)
            continue

        print(f"[INFO] Round 1 candidates for lock_url={lock_url}:")
        for u in candidate_urls:
            print(f"  - {u}")

        # ---------- Round 2: reverification on candidates ----------
        print(f"[INFO] Starting reverification round for lock_url={lock_url}")
        check_results_round2 = run_iteration_for_lock(lock_url, candidate_urls)

        verified_members = []
        for url in candidate_urls:
            count_value = check_results_round2.get(url)
            if count_value is not None and count_value >= MEMCHECK_THRESHOLD:
                verified_members.append(url)
            else:
                print(f"[INFO] {url} failed reverification and will be excluded.")

        # Final group: lock_url + verified members
        group_members = [lock_url] + verified_members
        group_members = list(set(group_members))

        print(f"[INFO] Final group for lock_url={lock_url}:")
        for m in group_members:
            print(f"  - {m}")

        groups.append({"lock_url": lock_url, "members": group_members})

        # Remove only the verified group members (including lock_url) from remaining.
        # Candidates that failed reverification stay in 'remaining' and may be
        # grouped with another lock_url in later iterations.
        for url in group_members:
            remaining.discard(url)

    if remaining:
        print("\n[WARN] Some instances remained ungrouped (should not normally happen):")
        for u in remaining:
            print(f"  - {u}")

    return groups


# ============================
# Main
# ============================

def main():
    global MEMCHECK_THRESHOLD

    # TODO: populate INSTANCE_URLS with real URLs before running.
    if not INSTANCE_URLS:
        print("[ERROR] INSTANCE_URLS is empty. Populate it with your instance URLs.")
        return

    # Set your empirically determined threshold here when actually running:
    MEMCHECK_THRESHOLD = None  # e.g., MEMCHECK_THRESHOLD = 800

    groups = identify_server_coverage(INSTANCE_URLS)

    print("\n[FINAL RESULT] Server coverage groups:")
    for idx, g in enumerate(groups, start=1):
        print(f"\n  Group {idx}: lock_url={g['lock_url']}")
        for member in g["members"]:
            print(f"    - {member}")


if __name__ == "__main__":
    main()

