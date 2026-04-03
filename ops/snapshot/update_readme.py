#!/usr/bin/env python3
from __future__ import annotations
"""
Update the snapshot table in README.md.

Inserts a new row at the TOP of the target environment's snapshot table.

Environment variables:
  ENVIRONMENT    - mainnet | hoodi
  SNAPSHOT_NAME  - e.g. snapshot-20260225-1
  BASE_HEIGHT    - L2 geth block height (L2 Base Height)
  L1_MSG_HEIGHT  - l1_msg_start_height from indexer API
  DERIV_HEIGHT   - derivation_start_height from indexer API
  METRICS_FILE   - (optional) path to write Prometheus metrics
                   default: /tmp/morph_snapshot_metrics.prom
                   metrics_server.py reads this file and serves it on :6060/metrics

Usage:
  python3 ops/snapshot/update_readme.py <path-to-README.md>
"""

import os
import re
import sys
import time

# ── Constants ─────────────────────────────────────────────────────────────────

CDN_BASE = "https://snapshot.morphl2.io"

SECTION_MARKERS = {
    "mainnet": "**For mainnet**",
    "hoodi":   "**For hoodi testnet**",
}

METRICS_FILE = os.environ.get("METRICS_FILE", "/tmp/morph_snapshot_metrics.prom")

# ── Metrics ───────────────────────────────────────────────────────────────────

def write_metric(status: int, environment: str, snapshot_name: str) -> None:
    """Write Prometheus metrics to METRICS_FILE. status: 1=success, 0=failure."""
    ts = int(time.time())
    labels = f'environment="{environment}",snapshot="{snapshot_name}"'
    content = (
        "# HELP morph_snapshot_readme_update_status 1 if last README update succeeded, 0 if failed\n"
        "# TYPE morph_snapshot_readme_update_status gauge\n"
        f"morph_snapshot_readme_update_status{{{labels}}} {status}\n"
        "# HELP morph_snapshot_readme_update_timestamp_seconds Unix timestamp of last run\n"
        "# TYPE morph_snapshot_readme_update_timestamp_seconds gauge\n"
        f"morph_snapshot_readme_update_timestamp_seconds{{{labels}}} {ts}\n"
    )
    os.makedirs(os.path.dirname(os.path.abspath(METRICS_FILE)), exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        f.write(content)

# ── README update ─────────────────────────────────────────────────────────────

def insert_row_content(content: str, section_marker: str, new_row: str) -> str:
    """
    In-memory version: takes the README content as a string, inserts new_row
    after the table separator in the target section, returns updated content.
    """
    lines     = content.splitlines(keepends=True)
    in_section = False
    inserted   = False
    result     = []

    for line in lines:
        result.append(line)

        if section_marker in line:
            in_section = True

        if in_section and not inserted and re.match(r"^\|[\s:|-]+\|", line):
            result.append(new_row + "\n")
            inserted   = True
            in_section = False

    if not inserted:
        raise RuntimeError(
            f"Could not find table separator for section: {section_marker!r}"
        )

    return "".join(result)


def insert_row(readme_path: str, section_marker: str, new_row: str) -> None:
    """File-based wrapper around insert_row_content."""
    with open(readme_path, "r") as f:
        content = f.read()

    updated = insert_row_content(content, section_marker, new_row)

    with open(readme_path, "w") as f:
        f.write(updated)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <README.md path>", file=sys.stderr)
        sys.exit(1)

    readme_path = sys.argv[1]

    # Validate required env vars
    missing = [v for v in ("ENVIRONMENT", "SNAPSHOT_NAME", "BASE_HEIGHT", "L1_MSG_HEIGHT", "DERIV_HEIGHT")
               if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        write_metric(0, os.environ.get("ENVIRONMENT", "unknown"),
                     os.environ.get("SNAPSHOT_NAME", "unknown"))
        sys.exit(1)

    environment   = os.environ["ENVIRONMENT"]
    snapshot_name = os.environ["SNAPSHOT_NAME"]
    base_height   = os.environ["BASE_HEIGHT"]
    l1_msg_height = os.environ["L1_MSG_HEIGHT"]
    deriv_height  = os.environ["DERIV_HEIGHT"]

    # Validate environment
    if environment not in SECTION_MARKERS:
        print(f"ERROR: Unknown environment: {environment!r}. Must be: {' | '.join(SECTION_MARKERS)}",
              file=sys.stderr)
        write_metric(0, environment, snapshot_name)
        sys.exit(1)

    section_marker = SECTION_MARKERS[environment]
    url = f"{CDN_BASE}/{environment}/{snapshot_name}.tar.gz"
    new_row = f"| [{snapshot_name}]({url}) | {deriv_height} | {l1_msg_height} | {base_height} |"

    try:
        insert_row(readme_path, section_marker, new_row)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        write_metric(0, environment, snapshot_name)
        sys.exit(1)

    print(f"✅ Inserted new row into [{environment}] table:")
    print(f"   {new_row}")

    write_metric(1, environment, snapshot_name)
    print(f"📊 Metrics written to: {METRICS_FILE}")


if __name__ == "__main__":
    main()

