#!/usr/bin/env python3
from __future__ import annotations
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
  2. Copy ops/snapshot/snapshot.env.example for each environment and fill in values:
       cp ops/snapshot/snapshot.env.example ops/snapshot/snapshot-mainnet.env
       cp ops/snapshot/snapshot.env.example ops/snapshot/snapshot-hoodi.env

  3. Copy ecosystem.config.js.example, set ENV_FILE and script path, then:
       pm2 start /data/morph-hoodi/ecosystem.config.js
       pm2 save
"""

import hashlib
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

    # SNAPSHOT_DAYS: comma-separated days of month to run (default: 13,28).
    # On other days the script exits immediately — prevents accidental runs on pm2 start.
    # Set SNAPSHOT_DAYS=any to bypass this check (e.g. for manual testing).
    snapshot_days_env = os.environ.get("SNAPSHOT_DAYS", "13,18")
    if snapshot_days_env.strip().lower() != "any":
        allowed_days = {int(d.strip()) for d in snapshot_days_env.split(",")}
        today = datetime.now(timezone.utc).day
        if today not in allowed_days:
            print(f"Today is day {today}, not in SNAPSHOT_DAYS={snapshot_days_env}. Exiting.")
            sys.exit(0)

    environment = os.environ.get("ENVIRONMENT", "mainnet")
    morph_home  = os.environ.get("MORPH_HOME", "")
    s3_bucket   = os.environ.get("S3_BUCKET", "")

    missing = [k for k, v in [("MORPH_HOME", morph_home), ("S3_BUCKET", s3_bucket)] if not v]
    if missing:
        for k in missing:
            print(f"ERROR: {k} is required", file=sys.stderr)
        sys.exit(1)

    # GETH_DB_DIR / NODE_DB_DIR point directly to the directories that will be
    # packed into the snapshot (as geth/ and data/ respectively).
    # Use `or` so that empty-string values in the env file also fall back to defaults.
    geth_db_dir   = os.environ.get("GETH_DB_DIR") or os.path.join(morph_home, "geth-data")
    node_db_dir   = os.environ.get("NODE_DB_DIR") or os.path.join(morph_home, "node-data", "data")

    # All temp files live under SNAPSHOT_WORK_DIR:
    #   staging/  — copytree target, deleted after compression
    #   snapshot.tar.gz — compressed output, deleted after S3 upload
    work_base     = os.environ.get("SNAPSHOT_WORK_DIR") or "/data/snapshot_work"
    work_dir      = os.path.join(work_base, "staging")
    snapshot_file = os.path.join(work_base, "snapshot.tar.gz")

    # Safety check: SNAPSHOT_WORK_DIR must not overlap with actual data directories.
    # The script deletes and recreates work_base at startup — if work_base IS or CONTAINS
    # a data directory, that data will be wiped. Placing work_base *inside* MORPH_HOME
    # (as a dedicated subdirectory) is safe as long as it doesn't overlap with geth/node data.
    def _is_subpath(child: str, parent: str) -> bool:
        child  = os.path.realpath(child)
        parent = os.path.realpath(parent)
        return child == parent or child.startswith(parent.rstrip("/") + "/")

    # Only block overlap with the actual data dirs, not with MORPH_HOME itself.
    protected = {"GETH_DB_DIR": geth_db_dir, "NODE_DB_DIR": node_db_dir}
    for var, path in protected.items():
        if not path:
            continue
        if _is_subpath(path, work_base) or _is_subpath(work_base, path):
            print(
                f"ERROR: SNAPSHOT_WORK_DIR={work_base!r} overlaps with {var}={path!r}.\n"
                f"  SNAPSHOT_WORK_DIR must be a dedicated directory outside all data paths.",
                file=sys.stderr,
            )
            sys.exit(1)

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
        services_stopped = True  # morph-node is down; exception handler must restart it

        # Stop morph-geth cleanly so geth can flush the snapshot journal to disk
        # (BlockChain.Stop → snaps.Journal) before prune or copy begins.
        # pm2 stop sends SIGTERM but returns immediately — geth may still be running.
        # Poll the geth LOCK file: it exists as long as geth holds the datadir lock,
        # and disappears only when the process has fully exited.
        #
        # IMPORTANT: For GETH_PRUNE=true to work, morph-geth must have
        # kill_timeout: 120000 in its ecosystem.config.js so PM2 does not
        # SIGKILL geth before the snapshot journal is written to disk.
        geth_lock = os.path.join(geth_db_dir, "geth", "LOCK")
        print("  Stopping morph-geth (waiting for LOCK file to disappear, up to 120s)...")
        run(["pm2", "stop", "morph-geth"])
        for i in range(120):
            if not os.path.exists(geth_lock):
                print(f"  morph-geth exited after {i}s")
                break
            time.sleep(1)
        else:
            print("  WARNING: geth LOCK file still present after 120s — proceeding anyway")

        print("✅ Services stopped")

        # ── Step 1.5: Optional prune (full node only) ─────────────────────────
        # Set GETH_PRUNE=true in snapshot.env to run `geth snapshot prune-state`
        # before copying data.  Leave unset (or false) for archive nodes.
        geth_bin = os.environ.get("GETH_BIN") or "geth"
        if os.environ.get("GETH_PRUNE", "").lower() in ("1", "true", "yes"):
            print("\n[1.5/6] Pruning geth state (may take a while)...")
            run([geth_bin, "snapshot", "prune-state", "--datadir", geth_db_dir])
            print("✅ Prune complete")
        else:
            print("\n[1.5/6] Skipping prune (GETH_PRUNE not set)")

        # ── Step 2: Create snapshot ───────────────────────────────────────────
        print("\n[2/6] Creating snapshot...")
        named_dir = os.path.join(work_base, snapshot_name)
        for d in [work_dir, named_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)
        os.makedirs(work_dir)

        # geth: only chaindata is needed for a snapshot
        geth_src = os.path.join(geth_db_dir, "geth", "chaindata")
        geth_dst = os.path.join(work_dir, "geth", "chaindata")
        print(f"  Copying geth chaindata: {geth_src}  (may take a while...)")
        shutil.copytree(geth_src, geth_dst)
        geth_size = subprocess.check_output(["du", "-sh", geth_dst]).decode().split()[0]
        print(f"  ✅ geth chaindata copied: {geth_size}")

        # node: only the 5 essential db directories
        node_dst = os.path.join(work_dir, "data")
        os.makedirs(node_dst)
        for db in ["blockstore.db", "cs.wal", "state.db", "tx_index.db", "evidence.db"]:
            src = os.path.join(node_db_dir, db)
            dst = os.path.join(node_dst, db)
            print(f"  Copying {db}...")
            shutil.copytree(src, dst)
        node_size = subprocess.check_output(["du", "-sh", node_dst]).decode().split()[0]
        print(f"  ✅ node data copied: {node_size}")

        # Rename staging/ to snapshot_name so the tar extracts to a named directory.
        os.rename(work_dir, named_dir)

        print(f"  Compressing to {snapshot_file}  (may take a while...)")
        run(["tar", "-czf", snapshot_file, "-C", work_base, snapshot_name])
        shutil.rmtree(named_dir)
        size = subprocess.check_output(["du", "-sh", snapshot_file]).decode().split()[0]
        print(f"✅ Snapshot created: {size}")

        # ── Step 3: Upload to S3 ──────────────────────────────────────────────
        print("\n[3/6] Uploading to S3...")

        # Compute SHA256 of the archive for integrity verification.
        print(f"  Computing SHA256 of {snapshot_file}  (may take a while...)")
        sha256 = hashlib.sha256()
        with open(snapshot_file, "rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                sha256.update(chunk)
        sha256_hex = sha256.hexdigest()
        sha256_file = snapshot_file + ".sha256"
        archive_basename = os.path.basename(snapshot_file)
        with open(sha256_file, "w") as f:
            f.write(f"{sha256_hex}  {archive_basename}\n")
        print(f"  SHA256: {sha256_hex}")

        s3_key        = f"{environment}/{snapshot_name}.tar.gz"
        s3_sha256_key = f"{environment}/{snapshot_name}.tar.gz.sha256"
        run(["aws", "s3", "cp", snapshot_file,  f"s3://{s3_bucket}/{s3_key}"])
        run(["aws", "s3", "cp", sha256_file, f"s3://{s3_bucket}/{s3_sha256_key}"])
        print(f"✅ Uploaded: s3://{s3_bucket}/{s3_key}")
        print(f"✅ Uploaded: s3://{s3_bucket}/{s3_sha256_key}")
        os.remove(snapshot_file)
        os.remove(sha256_file)
        print(f"✅ Removed local snapshot and sha256 files")

        # ── Step 4: Start geth, collect base_height ───────────────────────────
        print("\n[4/6] Starting morph-geth and collecting base_height...")
        run(["pm2", "start", "morph-geth"])
        geth_rpc = os.environ.get("GETH_RPC") or "http://127.0.0.1:8545"
        print("Waiting for geth RPC to be ready...")
        base_height = get_block_height(geth_rpc)
        os.environ["BASE_HEIGHT"] = str(base_height)
        print(f"✅ Geth base height: {base_height}")

        # ── Step 5: Start morph-node ──────────────────────────────────────────
        print("\n[5/6] Starting morph-node...")
        run(["pm2", "start", "morph-node"])
        print("✅ morph-node started")

        # ── Step 6: Update README via GitHub API ──────────────────────────────
        print("\n[6/6] Updating README snapshot table...")
        print("\n" + "─" * 60)
        print("  Snapshot summary (use this to create PR manually if step 6 fails):")
        print(f"  ENVIRONMENT     = {environment}")
        print(f"  SNAPSHOT_NAME   = {snapshot_name}")
        print(f"  BASE_HEIGHT     = {base_height}")
        print(f"  S3_KEY          = s3://{s3_bucket}/{s3_key}")
        print(f"  SHA256          = {sha256_hex}")
        print("  l1_msg_start_height and derivation_start_height will be")
        print("  printed by update_metadata.py — check log if PR creation fails.")
        print("─" * 60 + "\n")
        run([sys.executable, str(SCRIPT_DIR / "update_metadata.py")])

        if os.path.exists(work_base):
            shutil.rmtree(work_base)

        from update_readme import write_metric  # noqa: E402
        write_metric(1, environment, snapshot_name)

    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\nInterrupted (SIGINT received).", file=sys.stderr)
        else:
            print(f"\nERROR: {e}", file=sys.stderr)
        if services_stopped:
            print("Recovering services...")
            run(["pm2", "start", "morph-geth"], check=False)
            run(["pm2", "start", "morph-node"], check=False)
            print("Services recovered.")
        try:
            from update_readme import write_metric  # noqa: E402
            write_metric(0, environment, snapshot_name)
        except Exception:
            pass
        sys.exit(1)

    print(f"\n=== Done at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} ===")


if __name__ == "__main__":
    main()
