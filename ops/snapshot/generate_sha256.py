#!/usr/bin/env python3
from __future__ import annotations
"""
Backfill SHA256 checksum files for snapshot archives in S3.

Finds .tar.gz archives that are missing a corresponding .sha256 sidecar
and generates one by streaming the archive content directly from S3
(no local disk needed).

Usage:
  python3 generate_sha256.py --bucket my-bucket
  python3 generate_sha256.py --bucket my-bucket --env hoodi
  python3 generate_sha256.py --bucket my-bucket --key mainnet/snapshot-20260309-1.tar.gz
  python3 generate_sha256.py --bucket my-bucket --dry-run
  python3 generate_sha256.py --bucket my-bucket --force
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB, same as snapshot_make.py


def list_s3_keys(bucket: str, prefix: str, suffix: str) -> list[str]:
    """Return S3 keys matching the given prefix and suffix."""
    cmd = ["aws", "s3api", "list-objects-v2",
           "--bucket", bucket, "--output", "json"]
    if prefix:
        cmd += ["--prefix", prefix]

    keys: list[str] = []
    token = None
    while True:
        page_cmd = cmd if token is None else cmd + ["--continuation-token", token]
        result = subprocess.run(page_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: aws s3api failed: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)

        data = json.loads(result.stdout or "{}")
        for obj in data.get("Contents", []):
            if obj["Key"].endswith(suffix):
                keys.append(obj["Key"])

        if not data.get("IsTruncated"):
            break
        token = data.get("NextContinuationToken")

    return sorted(keys)


def human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_object_size(bucket: str, key: str) -> int:
    cmd = ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key,
           "--query", "ContentLength", "--output", "text"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def compute_sha256_streaming(bucket: str, key: str) -> str:
    """Stream an S3 object through hashlib.sha256 without touching disk."""
    s3_uri = f"s3://{bucket}/{key}"
    proc = subprocess.Popen(
        ["aws", "s3", "cp", s3_uri, "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    sha = hashlib.sha256()
    total = 0
    while True:
        chunk = proc.stdout.read(CHUNK_SIZE)
        if not chunk:
            break
        sha.update(chunk)
        total += len(chunk)

    proc.wait()
    if proc.returncode != 0:
        err = proc.stderr.read().decode().strip()
        raise RuntimeError(f"aws s3 cp failed for {s3_uri}: {err}")

    return sha.hexdigest()


def upload_sha256(bucket: str, sha256_key: str, sha256_hex: str,
                  archive_basename: str) -> None:
    """Write a sha256sum-compatible file and upload to S3."""
    content = f"{sha256_hex}  {archive_basename}\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sha256", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        s3_uri = f"s3://{bucket}/{sha256_key}"
        result = subprocess.run(
            ["aws", "s3", "cp", tmp_path, s3_uri],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"upload failed: {result.stderr.strip()}")
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill SHA256 checksums for S3 snapshot archives")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--env", default="",
                        help="Filter by environment prefix (e.g. hoodi, mainnet)")
    parser.add_argument("--key", default="",
                        help="Process a single S3 key instead of scanning")
    parser.add_argument("--dry-run", action="store_true",
                        help="List archives that need checksums without processing")
    parser.add_argument("--force", action="store_true",
                        help="Recompute even if .sha256 already exists")
    args = parser.parse_args()

    prefix = f"{args.env}/" if args.env else ""

    if args.key:
        if not args.key.endswith(".tar.gz"):
            print(f"ERROR: --key must end with .tar.gz, got: {args.key}",
                  file=sys.stderr)
            sys.exit(1)
        targets = [args.key]
    else:
        print(f"Listing archives in s3://{args.bucket}/{prefix or '*'} ...")
        archives = list_s3_keys(args.bucket, prefix, ".tar.gz")
        existing = set(list_s3_keys(args.bucket, prefix, ".tar.gz.sha256"))

        if args.force:
            targets = archives
        else:
            targets = [k for k in archives if k + ".sha256" not in existing]

        print(f"  Total archives:  {len(archives)}")
        print(f"  Already have .sha256: {len(archives) - len(targets)}")
        print(f"  Need processing: {len(targets)}")

    if not targets:
        print("\nNothing to do.")
        return

    if args.dry_run:
        print("\n[DRY RUN] Archives that would be processed:")
        for key in targets:
            size = get_object_size(args.bucket, key)
            print(f"  {key}  ({human_size(size)})")
        return

    print(f"\nProcessing {len(targets)} archive(s)...\n")
    for i, key in enumerate(targets, 1):
        basename = os.path.basename(key)
        sha256_key = key + ".sha256"
        size = get_object_size(args.bucket, key)
        print(f"[{i}/{len(targets)}] {key}  ({human_size(size)})")

        t0 = time.time()
        print(f"  Streaming and computing SHA256...")
        sha256_hex = compute_sha256_streaming(args.bucket, key)
        elapsed = time.time() - t0
        print(f"  SHA256: {sha256_hex}  ({elapsed:.1f}s)")

        upload_sha256(args.bucket, sha256_key, sha256_hex, basename)
        print(f"  Uploaded: s3://{args.bucket}/{sha256_key}\n")

    print(f"Done. Processed {len(targets)} archive(s).")


if __name__ == "__main__":
    main()
