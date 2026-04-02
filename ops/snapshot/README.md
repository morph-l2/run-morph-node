# Snapshot Automation

> 中文版请见 [README.zh.md](./README.zh.md)

Automatically creates a node snapshot every two weeks and syncs the relevant parameters to README.md for users to download.

## Background

Manually creating snapshots is error-prone and tedious. This solution automates the entire process using a server-side cron job and the GitHub REST API — no GitHub Actions or git CLI required.

## Directory Structure

```
run-morph-node/
├── README.md                           # snapshot table is updated here
└── ops/snapshot/
    ├── README.md                       # this document
    ├── README.zh.md                    # Chinese version
    ├── snapshot.env.example            # environment variable template (copy one per environment)
    ├── ecosystem.config.js.example     # PM2 process config template
    ├── snapshot_make.py                # entry point: stop → snapshot → upload → restart → update README
    ├── update_metadata.py              # fetches indexer API data and orchestrates the full update flow
    ├── update_readme.py                # pure table-update logic (imported by update_metadata.py)
    ├── metrics_server.py               # persistent HTTP server exposing metrics on :6060/metrics
    └── list_snapshots.py               # utility to list uploaded snapshots in S3
```

## Workflow

```
Server cron job (1st and 15th of each month)
        │
        ▼
  ops/snapshot/snapshot_make.py
    [1] stop morph-node, morph-geth
    [2] copy chain data:
        - geth: chaindata only  →  snapshot/geth/chaindata/
        - node: blockstore.db, cs.wal, state.db, tx_index.db, evidence.db  →  snapshot/data/
    [3] compress → upload to S3 as {environment}/{snapshot_name}.tar.gz
    [4] restart morph-geth → wait for RPC → collect base_height
    [5] restart morph-node
    [6] call update_metadata.py
        │  BASE_HEIGHT, SNAPSHOT_NAME
        ▼
  python3 update_metadata.py
  ┌─────────────────────────────────────────────────────┐
  │ 1. call explorer-indexer API:                       │
  │    GET /v1/batch/l1_msg_start_height/<base_height>  │
  │    GET /v1/batch/derivation_start_height/<base_height>│
  │ 2. fetch README.md content via GitHub API           │
  │ 3. insert new snapshot row at top of table          │
  │ 4. create branch + push updated file via GitHub API │
  │ 5. open PR via GitHub API                           │
  └─────────────────────────────────────────────────────┘
```

## Triggers

| Method | Description |
|---|---|
| Scheduled | Server cron job on the 1st and 15th of each month |
| Manual | SSH into the server and run `snapshot_make.py` directly |

## Multi-environment Support

| Environment | Default Indexer API | Override |
|---|---|---|
| mainnet | `https://explorer-indexer.morphl2.io` | `EXPLORER_INDEXER_URL` |
| hoodi | `https://explorer-indexer-hoodi.morphl2.io` | `EXPLORER_INDEXER_URL` |
| holesky | `https://explorer-indexer-holesky.morphl2.io` | `EXPLORER_INDEXER_URL` |

Each environment runs its own cron job with its own env file. S3 paths and README table sections are automatically scoped by environment.

Set `EXPLORER_INDEXER_URL` to an internal/intranet URL if the default public endpoint is not reachable from the node server.

## Deployment

### 1. Copy Scripts to the Node Server

The node server does not require git. Copy the scripts manually:

```bash
# copy all scripts to the data directory of each environment
scp ops/snapshot/*.py user@server:/data/morph-hoodi/
```

### 2. Create the Environment File

Copy the template into the environment's data directory and fill in the values:

```bash
cp ops/snapshot/snapshot.env.example /data/morph-hoodi/snapshot.env
vi /data/morph-hoodi/snapshot.env
```

All available variables are documented in [`snapshot.env.example`](./snapshot.env.example).

> ⚠️ **`SNAPSHOT_WORK_DIR` must NOT be set to `MORPH_HOME` or any data directory.**
> The script deletes and recreates this directory at startup. Setting it incorrectly will cause data loss.
> Use a dedicated subdirectory, e.g. `SNAPSHOT_WORK_DIR=/data/morph-hoodi/snapshot_work`.

These files must **not** be committed to git (add `*.env` to `.gitignore`).

Also recommended: enable **"Automatically delete head branches"** under repo Settings → General. Branches will be deleted automatically after a PR is merged.

### 3. Configure the Scheduled Job (PM2)

Copy the ecosystem template and edit `ENV_FILE` and `script` path for your environment:

```bash
cp ops/snapshot/ecosystem.config.js.example /data/morph-hoodi/ecosystem.config.js
vi /data/morph-hoodi/ecosystem.config.js
```

Start and persist:

```bash
pm2 start /data/morph-hoodi/ecosystem.config.js
pm2 save
```

To trigger manually for testing:

```bash
cd /data/morph-hoodi
nohup env ENV_FILE=/data/morph-hoodi/snapshot.env python3 /data/morph-hoodi/snapshot_make.py \
  > /tmp/snapshot.log 2>&1 &
tail -f /tmp/snapshot.log
```

### 4. Start the Metrics Server

Run `metrics_server.py` as a persistent pm2 process so it survives server reboots:

```bash
pm2 startup          # register pm2 itself as a system startup service (run once)
pm2 start python3 --name morph-snapshot-metrics -- /data/morph-hoodi/metrics_server.py
pm2 save
```

Once running, the metrics endpoint is available at `http://<server-ip>:6060/metrics`.

Exposed metrics:

| Metric | Type | Description |
|---|---|---|
| `morph_snapshot_readme_update_status` | gauge | 1 = success, 0 = failure |
| `morph_snapshot_readme_update_timestamp_seconds` | gauge | Unix timestamp of the last run |

Labels: `environment` (mainnet / hoodi / holesky), `snapshot` (snapshot name)

> Default metrics file path: `/tmp/morph_snapshot_metrics.prom`
> Override via the `METRICS_FILE` environment variable.

## Listing Snapshots in S3

```bash
# list all snapshots
python3 list_snapshots.py

# filter by environment
python3 list_snapshots.py --env hoodi

# specify bucket
python3 list_snapshots.py --env hoodi --bucket my-bucket-name
```

## Manual Recovery

If step 6 (README update) fails after a successful S3 upload, re-run `update_metadata.py` directly.
The snapshot summary is printed to the log before step 6 starts — use those values:

```bash
cd /data/morph-hoodi
ENVIRONMENT=hoodi \
SNAPSHOT_NAME=snapshot-20260312-1 \
BASE_HEIGHT=3904561 \
GH_TOKEN=ghp_xxx \
GITHUB_REPOSITORY=morph-l2/run-morph-node \
python3 /data/morph-hoodi/update_metadata.py
```

If the indexer API values are already known (visible in the log), skip the API call:

```bash
cd /data/morph-hoodi
ENVIRONMENT=hoodi \
SNAPSHOT_NAME=snapshot-20260312-1 \
BASE_HEIGHT=3904561 \
L1_MSG_HEIGHT=2388518 \
DERIV_HEIGHT=2401543 \
GH_TOKEN=ghp_xxx \
GITHUB_REPOSITORY=morph-l2/run-morph-node \
python3 /data/morph-hoodi/update_metadata.py
```

## Key Design Decisions

- **`base_height` is collected after geth restarts**: querying the RPC after the snapshot is created and geth is started alone gives the actual block state of the snapshot. `morph-node` is started only after the height is confirmed.
- **Only essential data is included in the snapshot**: geth `chaindata` only; node data includes `blockstore.db`, `cs.wal`, `state.db`, `tx_index.db`, `evidence.db`. Lock files, node keys, and P2P peer lists are excluded.
- **Snapshot extracts to a named directory**: the tar archive extracts to `{snapshot_name}/geth/` and `{snapshot_name}/data/`, matching the archive filename.
- **Fallback recovery on failure**: if the snapshot or upload fails, `snapshot_make.py` attempts to restart both services to avoid prolonged downtime.
- **No GitHub Actions or git CLI required**: `update_metadata.py` uses the GitHub REST API directly — the server only needs Python 3.7+.
- **New entries are inserted at the top of the table**: the latest snapshot always appears in the first row.
- **Changes are merged via PR, not direct push**: a new branch is created and a PR is opened, preserving review opportunity.
- **Per-environment env files**: each environment and snapshot type has its own `snapshot.env` file, specified via `ENV_FILE`.
