#!/usr/bin/env python3
"""
Prepare attacker instance sets for the Target Victim Locator.

Step 1:
  Query each attacker instance's /info endpoint to retrieve its CPU information:
    {
      "cpu_brand": "<string>",
      "parsed_freq": <float or null>  # frequency in Hz
    }

  Define CPU *architecture* as the pair (cpu_brand, parsed_freq).
  Instances are grouped into sets S1, S2, ..., Sm based on this pair.
  Two instances are in the same architecture set iff BOTH cpu_brand and
  parsed_freq are identical.

Step 2:
  Load server-sharing relationships (from the Server Coverage Identifier) and,
  within each architecture set, keep only one representative instance per
  physical server.

Output:
  JSON file with one entry per architecture set, including:
    - cpu_brand
    - parsed_freq
    - instances: list of attacker URLs (one representative per server)
"""

import argparse
import concurrent.futures
import json
import sys
from typing import Dict, List, Optional, Tuple

import requests


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare attacker sets based on (cpu_brand, parsed_freq) with one representative per server."
    )
    parser.add_argument(
        "--urls-file",
        required=True,
        help="Path to a text file containing attacker instance base URLs (one per line).",
    )
    parser.add_argument(
        "--server-groups-file",
        required=True,
        help="Path to a JSON file containing server-sharing groups "
             "(output from the Server Coverage Identifier).",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to the JSON file where the architecture-based sets will be written.",
    )
    parser.add_argument(
        "--info-endpoint",
        default="info",
        help="Relative info endpoint to query on each instance (default: 'info').",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds for /info (default: 10.0).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_urls(path: str) -> List[str]:
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def build_info_url(base_url: str, info_endpoint: str) -> str:
    base = base_url.rstrip("/")
    ep = info_endpoint.lstrip("/")
    return f"{base}/{ep}"


# ---------------------------------------------------------------------------
# /info query and architecture grouping
# ---------------------------------------------------------------------------

def fetch_cpu_info(
    base_url: str,
    info_endpoint: str,
    timeout: float,
) -> Tuple[Optional[str], Optional[float]]:
    """
    Query base_url/info_endpoint and return (cpu_brand, parsed_freq).

    Expected JSON:
        {
          "cpu_brand": "AMD EPYC ...",
          "parsed_freq": 2450000000.0
        }

    Returns (None, None) on error or missing cpu_brand.
    """
    info_url = build_info_url(base_url, info_endpoint)
    try:
        resp = requests.get(info_url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[WARN] Failed to fetch /info from {info_url}: {e}", file=sys.stderr)
        return None, None

    cpu_brand = data.get("cpu_brand")
    parsed_freq = data.get("parsed_freq")  # may be None

    if cpu_brand is None:
        print(f"[WARN] No 'cpu_brand' in /info response from {info_url}", file=sys.stderr)
        return None, None

    print(f"[INFO] {base_url} -> cpu_brand='{cpu_brand}', parsed_freq={parsed_freq}")
    return cpu_brand, parsed_freq


def group_by_architecture(
    urls: List[str],
    info_endpoint: str,
    timeout: float,
) -> Dict[Tuple[str, Optional[float]], List[str]]:
    """
    Query /info for each URL and group URLs by architecture key:
        arch_key = (cpu_brand, parsed_freq)

    Returns:
      arch_to_urls: {
        (cpu_brand, parsed_freq): [url1, url2, ...],
        ...
      }
    """
    arch_to_urls: Dict[Tuple[str, Optional[float]], List[str]] = {}

    def worker(u: str):
        return u, fetch_cpu_info(u, info_endpoint, timeout)

    workers = max(1, len(urls))  # one worker per URL; no external cap
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(worker, u): u for u in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url, (brand, freq) = future.result()

            if brand is None:
                # If brand is missing, we treat it as "unknown"; freq is ignored.
                arch_key = ("unknown", None)
            else:
                # Architecture = (cpu_brand, parsed_freq), even if parsed_freq is None.
                arch_key = (brand, freq)

            arch_to_urls.setdefault(arch_key, []).append(url)

    # Logging summary
    for (brand, freq), urls_for_arch in arch_to_urls.items():
        print(
            f"[INFO] Architecture (brand='{brand}', parsed_freq={freq}): "
            f"{len(urls_for_arch)} instances"
        )

    return arch_to_urls


# ---------------------------------------------------------------------------
# Server group handling
# ---------------------------------------------------------------------------

def load_server_groups(path: str) -> List[dict]:
    """
    Load server-sharing groups from JSON.

    Expected structure (as produced by the Server Coverage Identifier):

      [
        {
          "lock_url": "https://...",
          "members": ["https://instance-1", "https://instance-2", ...]
        },
        ...
      ]

    Only 'members' is required here.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Server groups JSON must be a list of group objects.")

    return data


def build_url_to_group_id(groups: List[dict]) -> Dict[str, int]:
    """
    Build a mapping from URL -> group_id (index in groups list).

    If a URL appears in multiple groups (should not normally happen),
    the last group id wins.
    """
    url_to_group: Dict[str, int] = {}
    for gid, group in enumerate(groups):
        members = group.get("members", [])
        for url in members:
            url_to_group[url] = gid
    return url_to_group


def deduplicate_by_server_within_arch_sets(
    arch_to_urls: Dict[Tuple[str, Optional[float]], List[str]],
    url_to_group: Dict[str, int],
) -> List[dict]:
    """
    For each architecture set, keep only one representative instance per server group.

    Input:
      arch_to_urls: {
        (cpu_brand, parsed_freq): [url1, url2, ...],
        ...
      }

    Returns:
      cpu_sets: [
        {
          "cpu_brand": <str>,
          "parsed_freq": <float or null>,
          "instances": [url_rep1, url_rep2, ...]  # one per server
        },
        ...
      ]
    """
    cpu_sets: List[dict] = []

    for (cpu_brand, parsed_freq), urls in arch_to_urls.items():
        group_to_rep: Dict[str, str] = {}

        for url in urls:
            if url in url_to_group:
                gid = f"group-{url_to_group[url]}"
            else:
                # URL not covered by any server group; treat as its own singleton
                gid = f"single-{url}"

            if gid not in group_to_rep:
                group_to_rep[gid] = url

        reps = list(group_to_rep.values())

        print(
            f"[INFO] Architecture (brand='{cpu_brand}', parsed_freq={parsed_freq}): "
            f"{len(urls)} instances, {len(reps)} representatives after server deduplication"
        )

        cpu_sets.append(
            {
                "cpu_brand": cpu_brand,
                "parsed_freq": parsed_freq,
                "instances": sorted(reps),
            }
        )

    return cpu_sets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # 1) Load attacker instance URLs
    urls = load_urls(args.urls_file)
    if not urls:
        print("[ERROR] No attacker URLs loaded. Check --urls-file.", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Loaded {len(urls)} attacker instance URLs from {args.urls_file}")

    # 2) Group by architecture = (cpu_brand, parsed_freq)
    arch_to_urls = group_by_architecture(
        urls=urls,
        info_endpoint=args.info_endpoint,
        timeout=args.timeout,
    )

    # 3) Load server-sharing groups and build URL -> group_id mapping
    groups = load_server_groups(args.server_groups_file)
    url_to_group = build_url_to_group_id(groups)

    print(f"[INFO] Loaded {len(groups)} server-sharing groups from {args.server_groups_file}")
    print(f"[INFO] URL->group mapping covers {len(url_to_group)} URLs")

    # 4) For each architecture set, keep one representative per server group
    cpu_sets = deduplicate_by_server_within_arch_sets(arch_to_urls, url_to_group)

    # 5) Save output
    output = {"cpu_sets": cpu_sets}

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"[INFO] Wrote architecture-based attacker sets to {args.output_file}")


if __name__ == "__main__":
    main()

