#!/usr/bin/env python3
from __future__ import annotations
"""
List snapshot files in S3 bucket.

Usage:
  python3 list_snapshots.py
  python3 list_snapshots.py --env hoodi
  python3 list_snapshots.py --env mainnet --bucket my-bucket
"""

import argparse
import subprocess
import json
import sys


def list_snapshots(bucket: str, prefix: str = "") -> list[dict]:
    cmd = ["aws", "s3api", "list-objects-v2",
           "--bucket", bucket,
           "--query", "Contents[?ends_with(Key, '.tar.gz')].[Key,Size,LastModified]",
           "--output", "json"]
    if prefix:
        cmd += ["--prefix", prefix]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    items = json.loads(result.stdout or "[]") or []
    return [{"key": r[0], "size": r[1], "last_modified": r[2]} for r in items]


def human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def main() -> None:
    parser = argparse.ArgumentParser(description="List snapshots in S3 bucket")
    parser.add_argument("--bucket", default="morph-0582-morph-technical-department-snapshot",
                        help="S3 bucket name")
    parser.add_argument("--env", default="",
                        help="Filter by environment prefix (e.g. hoodi, mainnet)")
    args = parser.parse_args()

    prefix = f"{args.env}/" if args.env else ""
    snapshots = list_snapshots(args.bucket, prefix)

    if not snapshots:
        print(f"No snapshots found in s3://{args.bucket}/{prefix}")
        return

    snapshots.sort(key=lambda x: x["last_modified"], reverse=True)

    print(f"\nSnapshots in s3://{args.bucket}/{prefix or '*'}")
    print(f"{'Last Modified':<28} {'Size':>10}  Key")
    print("-" * 80)
    for s in snapshots:
        print(f"{s['last_modified']:<28} {human_size(s['size']):>10}  {s['key']}")
    print(f"\nTotal: {len(snapshots)} snapshot(s)")


if __name__ == "__main__":
    main()
