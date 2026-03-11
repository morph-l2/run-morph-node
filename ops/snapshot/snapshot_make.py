#!/usr/bin/env python3
"""
ops/snapshot/snapshot_make.py

Runs on the node server via cron (1st and 15th of each month).

Responsibilities:
  1. Stop morph-geth and morph-node
  2. Create and compress a snapshot of chain data
  3. Upload the snapshot to S3
  4. Restart morph-geth, wait for RPC, collect base_height
  5. Restart morph-node
  6. Call update_metadata.py to open a PR updating the README snapshot table

Setup:
  1. Clone the repo to /data/run-morph-node on the node server
  2. Copy ops/snapshot/snapshot.env.example to ops/snapshot/snapshot.env and fill in values
     For multiple environments/types, use separate files and pass via ENV_FILE:
       cp ops/snapshot/snapshot.env.example ops/snapshot/snapshot-mainnet.env
       cp ops/snapshot/snapshot.env.example ops/snapshot/snapshot-hoodi.env

  3. Add to crontab (one entry per environment / snapshot type):

     REPO=/data/run-morph-node/ops/snapshot

     # mainnet standard snapshot (uses default snapshot.env)
     0 2 1,15 * * python3 $REPO/snapshot_make.py >> /var/log/snapshot-mainnet.log 2>&1

     # mainnet mpt-snapshot
     0 3 1,15 * * ENV_FILE=$REPO/snapshot-mainnet-mpt.env \
       python3 $REPO/snapshot_make.py >> /var/log/snapshot-mainnet-mpt.log 2>&1

     # hoodi
     0 2 1,15 * * ENV_FILE=$REPO/snapshot-hoodi.env \
       python3 $REPO/snapshot_make.py >> /var/log/snapshot-hoodi.log 2>&1
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR   = SCRIPT_DIR.parent.parent

# ── Env file loader ────────────────────────────────────────────────────────────

def load_env_file(path: str) -> None:
    """Parse KEY=value lines (with or without 'export' prefix) into os.environ."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                if "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)
    except FileNotFoundError:
        print(f"WARNING: {path} not found, relying on existing environment variables")

# ── Shell helpers ──────────────────────────────────────────────────────────────

def run(args: list, check: bool = True) -> None:
    print(f"  $ {' '.join(str(a) for a in args)}")
    subprocess.run(args, check=check)

# ── Geth RPC ───────────────────────────────────────────────────────────────────

def get_block_height(rpc_url: str = "http://localhost:8545",
                     retries: int = 30, interval: int = 5) -> int:
    payload = json.dumps({
        "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
    }).encode()
    for i in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                rpc_url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())["result"]
                if result:
                    return int(result, 16)
        except Exception:
            pass
        print(f"  attempt {i}: geth not ready yet, retrying in {interval}s...")
        time.sleep(interval)
    raise RuntimeError("geth RPC did not become available in time")

# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    env_file = os.environ.get("ENV_FILE", str(SCRIPT_DIR / "snapshot.env"))
    load_env_file(env_file)

    environment       = os.environ.get("ENVIRONMENT", "mainnet")
    morph_home        = os.environ.get("MORPH_HOME", f"/data/{environment}")
    s3_bucket         = os.environ.get("S3_BUCKET", "")
    if not s3_bucket:
        print("ERROR: S3_BUCKET is required", file=sys.stderr)
        sys.exit(1)

    geth_data_dir     = os.path.join(morph_home, "geth-data")
    node_data_dir     = os.path.join(morph_home, "node-data")
    work_dir          = os.environ.get("SNAPSHOT_WORK_DIR", "/data/snapshot_work")
    snapshot_file     = os.environ.get("SNAPSHOT_FILE", "/data/snapshot.tar.gz")

    # SNAPSHOT_PREFIX allows different snapshot types to coexist:
    # e.g. "snapshot", "mpt-snapshot", "full-snapshot"
    snapshot_prefix   = os.environ.get("SNAPSHOT_PREFIX", "snapshot")
    date              = datetime.now(timezone.utc).strftime("%Y%m%d")
    snapshot_name     = f"{snapshot_prefix}-{date}-1"

    os.environ["SNAPSHOT_NAME"] = snapshot_name
    os.environ["ENVIRONMENT"]   = environment

    print(f"=== Morph Snapshot: {snapshot_name} ({environment}) ===")
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    gh_token = os.environ.get("GH_TOKEN", "")
    gh_repo  = os.environ.get("GITHUB_REPOSITORY", "")

    services_stopped = False
    try:
        # ── Step 0: Resolve snapshot_name before any destructive operation ────
        # Check GitHub now so that snapshot_name, S3 key, and branch all match.
        if gh_token and gh_repo:
            from update_metadata import resolve_snapshot_name
            snapshot_name = resolve_snapshot_name(gh_repo, environment, snapshot_name, gh_token)
            os.environ["SNAPSHOT_NAME"] = snapshot_name
            print(f"Resolved snapshot name: {snapshot_name}")

        # ── Step 1: Stop services ─────────────────────────────────────────────
        print("\n[1/6] Stopping services...")
        run(["pm2", "stop", "morph-node"])
        run(["pm2", "stop", "morph-geth"])
        services_stopped = True
        time.sleep(10)
        print("✅ Services stopped")

        # ── Step 2: Create snapshot ───────────────────────────────────────────
        print("\n[2/6] Creating snapshot...")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        shutil.copytree(os.path.join(geth_data_dir, "geth"), os.path.join(work_dir, "geth"))
        shutil.copytree(os.path.join(node_data_dir, "data"), os.path.join(work_dir, "data"))

        print(f"Compressing to {snapshot_file}...")
        run(["tar", "-czf", snapshot_file, "-C", work_dir, "."])
        shutil.rmtree(work_dir)
        size = subprocess.check_output(["du", "-sh", snapshot_file]).decode().split()[0]
        print(f"✅ Snapshot created: {size}")

        # ── Step 3: Upload to S3 ──────────────────────────────────────────────
        print("\n[3/6] Uploading to S3...")
        s3_key = f"{environment}/{snapshot_name}.tar.gz"
        run(["aws", "s3", "cp", snapshot_file, f"s3://{s3_bucket}/{s3_key}", "--no-progress"])
        print(f"✅ Uploaded: s3://{s3_bucket}/{s3_key}")

        # ── Step 4: Start geth, collect base_height ───────────────────────────
        print("\n[4/6] Starting morph-geth and collecting base_height...")
        run(["pm2", "start", "morph-geth"])
        print("Waiting for geth RPC to be ready...")
        base_height = get_block_height()
        os.environ["BASE_HEIGHT"] = str(base_height)
        print(f"✅ Geth base height: {base_height}")

        # ── Step 5: Start morph-node ──────────────────────────────────────────
        print("\n[5/6] Starting morph-node...")
        run(["pm2", "start", "morph-node"])
        print("✅ morph-node started")

        # ── Step 6: Update README via GitHub API ──────────────────────────────
        print("\n[6/6] Updating README snapshot table...")
        run([sys.executable, str(REPO_DIR / "ops" / "snapshot" / "update_metadata.py")])

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if services_stopped:
            print("Recovering services...")
            run(["pm2", "start", "morph-geth"], check=False)
            run(["pm2", "start", "morph-node"], check=False)
            print("Services recovered.")
        sys.exit(1)

    print(f"\n=== Done at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} ===")


if __name__ == "__main__":
    main()
