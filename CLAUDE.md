# run-morph-node

Morph L2 node operator toolkit. Provides Docker-based setup for running Morph nodes (standard and MPT), plus automated snapshot creation and distribution infrastructure.

## Project Structure

```
morph-node/          # Docker Compose setup for running a Morph node
  Makefile           # All node operations (run/stop/download-snapshot)
  docker-compose.yml # Service definitions: geth + node/validator
  .env               # Mainnet config
  .env_holesky       # Holesky testnet config
  .env_hoodi         # Hoodi testnet config
  .env_mpt           # MPT-specific overrides (loaded on top of env)
  entrypoint-geth.sh       # Standard geth startup script
  entrypoint-geth-mpt.sh   # MPT geth startup script (--morph-mpt flag)

ops/snapshot/        # Snapshot automation scripts (runs on server via cron/pm2)
  snapshot_make.py   # Entry point: stop → snapshot → S3 upload → restart → update README
  update_metadata.py # Fetches indexer API data, creates branch + PR via GitHub API
  update_readme.py   # In-memory README table insertion logic + Prometheus metrics
  metrics_server.py  # HTTP server exposing snapshot metrics on :6060/metrics
  snapshot.env.example  # Configuration reference

mainnet/hoodi/holesky/   # Chain genesis and config files (static, do not modify)
```

## Environments

| Environment | Makefile prefix | Snapshot CDN |
|-------------|-----------------|--------------|
| Mainnet     | (no prefix)     | snapshot.morphl2.io/mainnet |
| Hoodi testnet | `-hoodi`      | snapshot.morphl2.io/hoodi |
| Holesky testnet (legacy) | `-holesky` | snapshot.morphl2.io/holesky |

MPT variants use an additional `--env-file .env_mpt` overlay.

## Common Operations

```bash
# Run a node
cd morph-node
make run-hoodi-node           # hoodi standard
make run-mainnet-mpt-node     # mainnet MPT

# Download snapshot
make download-and-decompress-hoodi-snapshot
make download-and-decompress-mainnet-mpt-snapshot

# Stop
make stop-node
make stop-validator
```

## Snapshot Automation

Runs on a server via pm2, triggered on configured days of the month.

**Full flow:**
1. Stop morph-node + morph-geth (pm2)
2. tar geth-data + node-data → upload to S3
3. Restart geth → wait for RPC → collect `base_height`
4. Restart morph-node
5. Query indexer API for `l1_msg_start_height` and `derivation_start_height`
6. Push updated README row + open PR via GitHub API (no git CLI needed)

**Configuration:** Copy `ops/snapshot/snapshot.env.example` to the server data directory, fill in `S3_BUCKET`, `GH_TOKEN`, `MORPH_HOME`, `GITHUB_REPOSITORY`.

**Dry run (safe, no writes):**
```bash
DRY_RUN=1 ENVIRONMENT=mainnet SNAPSHOT_NAME=test-1 BASE_HEIGHT=123 \
  L1_MSG_HEIGHT=456 DERIV_HEIGHT=789 python3 ops/snapshot/update_metadata.py
```

## Code Conventions

- **Python**: stdlib only (no third-party deps), Python 3.9+. Use `urllib.request` for HTTP, not `requests`.
- **Shell scripts**: POSIX sh (`#!/bin/sh`), not bash. Use `set -e` for error handling.
- **Makefile**: Use `define`/`call` macros for repeated patterns. Always check for required tools before running.
- **Error handling**: Scripts must recover services if stopped (see `try/finally` pattern in `snapshot_make.py`).
- **Environment config**: Never hardcode paths or credentials. Always read from env vars with sensible defaults.

## Security

- **Never commit** `.env`, `snapshot.env`, or any file containing `GH_TOKEN`, `S3_BUCKET`, or AWS credentials.
- `GH_TOKEN` must be a Fine-grained PAT with only `Contents: Read/Write` and `Pull requests: Read/Write`.
- Snapshot automation opens PRs — it never merges directly to main.
- `jwt-secret.txt` is generated locally and never committed.

## Git Conventions

- Branch naming: `feat/`, `fix/`, `docs/` prefixes
- Snapshot automation branches: `snapshot/{environment}-{snapshot-name}`
- PRs require at least 1 approval before merging to main
- Commits are GPG-signed (configured in `~/.gitconfig`)
