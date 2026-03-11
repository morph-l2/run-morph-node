# Snapshot Automation

> 中文版请见 [README.zh.md](./README.zh.md)

Automatically creates a node snapshot every two weeks and syncs the relevant parameters to README.md for users to download.

## Background

Manually creating snapshots is error-prone and tedious. This solution automates the entire process using a server-side cron job and the GitHub REST API — no GitHub Actions or git CLI required.

## Directory Structure

```
run-morph-node/
├── README.md                         # snapshot table is updated here
└── ops/snapshot/
    ├── README.md                     # this document
    ├── README.zh.md                  # Chinese version
    ├── snapshot_make.py              # entry point: stop → snapshot → upload → restart → update README
    ├── update_metadata.py            # fetches indexer API data and orchestrates the full update flow
    ├── update_readme.py              # pure table-update logic (imported by update_metadata.py)
    └── metrics_server.py             # persistent HTTP server exposing metrics on :6060/metrics
```

## Workflow

```
Server cron job (1st and 15th of each month)
        │
        ▼
  ops/snapshot/snapshot_make.py
    [1] stop morph-node, morph-geth
    [2] create snapshot (tar geth + node data)
    [3] upload to S3
    [4] restart morph-geth → wait for RPC → collect base_height
    [5] restart morph-node
    [6] call update_metadata.py
        │  BASE_HEIGHT, SNAPSHOT_NAME
        ▼
  python3 update_metadata.py
  ┌─────────────────────────────────────────────────────┐
  │ 1. call internal explorer-indexer API:              │
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

| Environment | Indexer API (internal) |
|---|---|
| mainnet | `explorer-indexer.morphl2.io` |
| hoodi | `explorer-indexer-hoodi.morphl2.io` |
| holesky | `explorer-indexer-holesky.morphl2.io` |

Each environment has its own node server with its own cron job. S3 paths and README table sections are automatically scoped by environment.

## Deployment

### 1. Clone the Repository on the Node Server

```bash
git clone https://github.com/morphl2/run-morph-node.git /data/run-morph-node
```

### 2. Create the Environment File

Copy the template into the same directory and fill in the values:

```bash
cd /data/run-morph-node/ops/snapshot
cp snapshot.env.example snapshot.env
# edit snapshot.env and fill in GH_TOKEN, S3_BUCKET, ENVIRONMENT, etc.
```

For multiple environments or snapshot types, use separate files:

```bash
cp snapshot.env.example snapshot-hoodi.env
cp snapshot.env.example snapshot-mainnet-mpt.env
```

All available variables are documented in [`snapshot.env.example`](./snapshot.env.example). These files must **not** be committed to git (add `*.env` to `.gitignore`).

Also recommended: enable **"Automatically delete head branches"** under repo Settings → General. Branches will be deleted automatically after a PR is merged.

### 3. Configure the Scheduled Job (PM2)

Copy the ecosystem template and edit `ENV_FILE` and `script` path for your environment:

```bash
cp /data/run-morph-node/ops/snapshot/ecosystem.config.js.example /data/morph-hoodi/ecosystem.config.js
# edit ecosystem.config.js
```

Start and persist:

```bash
pm2 start /data/morph-hoodi/ecosystem.config.js
pm2 save
```

To trigger manually for testing:

```bash
pm2 restart snapshot-hoodi
pm2 logs snapshot-hoodi
```

### 4. Start the Metrics Server

Run `metrics_server.py` as a persistent pm2 process so it survives server reboots:

```bash
pm2 startup          # register pm2 itself as a system startup service (run once)
pm2 start python3 --name morph-snapshot-metrics -- /data/run-morph-node/ops/snapshot/metrics_server.py
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
> Override via the `METRICS_FILE` environment variable — applies to both `update_readme.py` and `metrics_server.py`.

## Key Design Decisions

- **`base_height` is collected after geth restarts**: querying the RPC after the snapshot is created and geth is started alone gives the actual block state of the snapshot, which is more accurate than querying before the stop. `morph-node` is started only after the height is confirmed.
- **Fallback recovery on failure**: if the snapshot or upload fails, a fallback step in `snapshot_make.py` attempts to restart both processes to avoid prolonged service interruption.
- **No GitHub Actions or git CLI required**: `update_metadata.py` uses the GitHub REST API directly — the server only needs Python 3. The `GH_TOKEN` is the only credential needed.
- **New entries are inserted at the top of the table**: the latest snapshot always appears in the first row for quick access.
- **Changes are merged via PR, not direct push**: a new branch is created and a PR is opened, preserving review opportunity and preventing automated scripts from writing directly to the main branch.


