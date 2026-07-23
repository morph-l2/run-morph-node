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
    snapshot_days_env = os.environ.get("SNAPSHOT_DAYS", "1,17")
    if snapshot_days_env.strip().lower() != "any":
        allowed_days = {int(d.strip()) for d in snapshot_days_env.split(",")}
        today = datetime.now().day
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

    # SNAPSHOT_WORK_DIR holds only the compressed archive (snapshot.tar.gz),
    # deleted after S3 upload. The snapshot is tarred directly from the live
    # data dirs — no staging copy — so this dir needs room for the archive
    # (~1/2 of the source data after gzip), not a full second copy.
    work_base     = os.environ.get("SNAPSHOT_WORK_DIR") or "/data/snapshot_work"
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
    date              = datetime.now().strftime("%Y%m%d")
    snapshot_name     = f"{snapshot_prefix}-{date}-1"

    os.environ["SNAPSHOT_NAME"] = snapshot_name
    os.environ["ENVIRONMENT"]   = environment

    print(f"=== Morph Snapshot: {snapshot_name} ({environment}) ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

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
        # NOTE: We tar directly from the live data directories instead of first
        # copying them into a staging area. On a single-disk host, an intermediate
        # copy would need ~600G on top of the source data plus the archive itself,
        # blowing past the disk. Streaming straight into tar drops the peak usage
        # to (source data + archive) only. geth is stopped at this point, so the
        # data directories are read-only and safe to archive in place.
        #
        # --transform rewrites each member path so the archive still extracts to:
        #   <snapshot_name>/geth/chaindata/...
        #   <snapshot_name>/data/<db>/...
        # matching the layout produced by the previous copytree approach, which the
        # download/decompress tooling depends on.
        print("\n[2/6] Creating snapshot...")
        os.makedirs(work_base, exist_ok=True)
        if os.path.exists(snapshot_file):
            os.remove(snapshot_file)

        # geth: only chaindata is needed for a snapshot
        geth_src = os.path.join(geth_db_dir, "geth", "chaindata")
        # node: the 6 essential db directories plus priv_validator_state.json.
        # The state file lives alongside the dbs under node_db_dir and MUST be
        # included — a validator restored without it can double-sign or refuse
        # to start (CometBFT refuses to overwrite a missing/blank state file).
        node_dbs = ["blockstore.db", "cs.wal", "state.db", "tx_index.db",
                    "evidence.db", "signatures.db"]
        node_members = node_dbs + ["priv_validator_state.json"]

        # A SINGLE tar -czf invocation compresses straight to .tar.gz — no
        # intermediate uncompressed .tar and no staging copy. This keeps peak
        # disk usage at (source data + final archive) instead of tripling it.
        # geth is stopped here, so the data dirs are read-only and safe to read.
        #
        # tar walks multiple sources by interleaving -C (change dir) with the
        # member name that follows it. --transform is a global sed expression
        # applied to every member path; a single expression with two rules
        # rewrites both source groups into the layout the download tooling
        # expects (identical to the previous copytree output):
        #   chaindata               -> <snapshot_name>/geth/chaindata/...
        #   <db> / state file (node) -> <snapshot_name>/data/<name>...
        # | is the sed delimiter (never appears in these paths). The chaindata
        # rule is anchored (^chaindata) so it can't also match a node member.
        node_alt = "\\|".join(node_members)
        transform = (
            f"--transform=s|^chaindata|{snapshot_name}/geth/chaindata|;"
            f"s|^\\({node_alt}\\)|{snapshot_name}/data/\\1|"
        )

        print(f"  Archiving geth chaindata: {geth_src}")
        print(f"  Archiving node data ({node_db_dir}): {', '.join(node_members)}")
        print(f"  Compressing to {snapshot_file}  (may take a while...)")

        tar_cmd = ["tar", "-czf", snapshot_file, transform,
                   "-C", os.path.dirname(geth_src), os.path.basename(geth_src),
                   "-C", node_db_dir, *node_members]
        run(tar_cmd)
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

    print(f"\n=== Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} ===")


if __name__ == "__main__":
    main()
