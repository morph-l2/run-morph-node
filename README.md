# run-morph-node

`run-morph-node` is a repository designed to facilitate the deployment and management of Morph nodes using Docker. Morph is an innovative platform that enhances Ethereum Layer 2 scalability by combining optimistic rollups and zk technology, aiming to revolutionize consumer blockchain applications.

## Features

- **Dockerized Deployment**: Simplifies the process of setting up Morph nodes using Docker containers.
- **Network Support**: Provides configurations for both Mainnet and Hoodi testnet environments.
- **Execution Client Choice**: Run the node with either **geth** (`go-ethereum`) or **reth** (`morph-reth`) as the execution client.
- **Snapshot Synchronization**: Supports synchronizing node data from snapshots to expedite the setup process.

## Prerequisites

Before setting up a Morph node, ensure you have the following installed:

- **Docker**: Containerization platform to run the node.
- **Docker Compose**: Tool for defining and running multi-container Docker applications.

## Quick Start

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/morph-l2/run-morph-node.git
   ```

2. **Navigate to the Project Directory**:

   ```bash
   cd run-morph-node
   ```

3. **Configure Environment Variables**:

   Edit the `.env` file to set the appropriate values for your setup if needed. For instance, specify the `MORPH_HOME` if you plan to user your specified directory as your node data home. By default, it takes  `./mainnet` as the node data home for mainnet network.

4. **Download and Decompress Snapshot (Optional but Recommended)**:

- To expedite synchronization, download the latest snapshot:

    ```bash
    make download-and-decompress-mainnet-snapshot
    ```

- For Hoodi testnet, use the corresponding command:

    ```bash
    make download-and-decompress-hoodi-snapshot
    ```

- After downloading the snapshot, you need to manually place the decompressed data files in the appropriate node data directories. Alternatively, use the `quickstart-*` targets (e.g. `make quickstart-mainnet-node`) which handle snapshot download and placement automatically.
    - `make download-and-decompress-*` now extracts snapshots under network directories (`../mainnet` or `../hoodi`).
    - For example, if the snapshot folder is named `snapshot-20260415-1`, move the directory to the `MORPH_HOME` directories:
        ```
        mv ${MORPH_HOME}/snapshot-20260415-1/geth ${MORPH_HOME}/geth-data
        mv ${MORPH_HOME}/snapshot-20260415-1/data/* ${MORPH_HOME}/node-data/data
        ```

    - The folder structure will be like
        ```
        └── ${MORPH_HOME}
            ├── geth-data // data directory for geth
            │   └── geth // directory from snapshot/geth
            └── node-data // data directory for node
                ├── config
                │   ├── config.toml
                │   └── genesis.json
                └── data // data directory from snapshot/node
        ```

    - **Reth uses a different snapshot** (the `*-reth-*` rows in the snapshot
      table) with a different execution-client layout. Its tarball contains a
      `reth-data/` tree plus the same `data/` for the node. `static-nodes.json`
      is not in the snapshot; the `quickstart-*-reth-*` / `setup-snapshot-data-reth`
      helpers copy it from `geth-data/` into `reth-data/` for `--trusted-peers`.
      The folder structure will be like
        ```
        └── ${MORPH_HOME}
            ├── reth-data // data directory for reth
            │   ├── db // from snapshot/reth-data
            │   ├── static_files // from snapshot/reth-data
            │   ├── rocksdb // from snapshot/reth-data
            │   ├── morph // from snapshot/reth-data
            │   └── static-nodes.json // copied from geth-data, parsed into --trusted-peers
            └── node-data // data directory for node
                ├── config
                │   ├── config.toml
                │   └── genesis.json
                └── data // data directory from snapshot/node
        ```


5. **Run the Node**:

- Start the node using Docker Compose:

    ```bash
    make run-node
    ```

  For Hoodi testnet, run

    ```bash
    make run-hoodi-node
    ```

- This command will set up and run the node based on the configurations specified in your .env file.

### Running with reth instead of geth

The node can run with **reth** (`morph-reth`) as its execution client instead of
geth. Reth uses a **separate execution-client data directory** (`${MORPH_HOME}/reth-data`)
and, importantly, a **different snapshot** than geth (see the [Snapshot Information](#snapshot-information)
table — reth snapshots are the `*-reth-*` rows). The `morph-node` (derivation) side
is identical; only the execution client and its snapshot differ.

- Start a reth-backed node with Docker Compose:

    ```bash
    make run-reth-node        # mainnet
    make run-hoodi-reth-node  # hoodi
    ```

  Stop / remove:

    ```bash
    make stop-reth-node
    make rm-reth-node
    ```

- Or use a one-command quickstart (downloads the reth snapshot, places the data, and runs):

    ```bash
    make quickstart-mainnet-reth-node   # mainnet, Docker
    make quickstart-hoodi-reth-node     # hoodi, Docker
    ```

- **Binary mode** (build `morph-reth` from source with `cargo`, then run the binaries directly):

    ```bash
    make build-reth-all              # builds morph-reth + morphnode into ./bin
    make run-reth-node-binary        # mainnet
    make run-hoodi-reth-node-binary  # hoodi
    make stop-binary                 # stops geth/reth/morphnode
    # or one-command: make quickstart-mainnet-reth-node-binary / quickstart-hoodi-reth-node-binary
    ```

    `build-reth` clones `morph-reth` into `../morph-reth` and checks out a pinned
    tag `v$(RETH_VERSION)` (default `1.3.0`, kept in sync with the image in
    `docker-compose.reth.yml`) so the binary and Docker paths run the same version.
    Bump it in one place with `make set-versions RETH_VERSION=1.4.0 ...` (rewrites the
    compose image tag), or build a one-off with `make build-reth RETH_VERSION=1.4.0`.

`morph-reth` reads the boot nodes from `static-nodes.json` and passes them to
`--trusted-peers` (discovery is disabled). The snapshot does **not** contain
`static-nodes.json`, so the snapshot setup copies it from `${MORPH_HOME}/geth-data/static-nodes.json`
into `${MORPH_HOME}/reth-data/`. The reth launch command used by the entrypoint is:

```bash
morph-reth node \
  --chain <mainnet|hoodi> \
  --datadir $RETH_DATA_DIR \
  --http --http.addr 0.0.0.0 --http.port 8545 --http.corsdomain '*' \
  --http.api web3,eth,txpool,net,trace \
  --ws --ws.addr 0.0.0.0 --ws.port 8546 --ws.origins '*' \
  --ws.api web3,eth,txpool,net,trace \
  --authrpc.addr 0.0.0.0 --authrpc.port 8551 --authrpc.jwtsecret /jwt-secret.txt \
  --disable-discovery --nat none \
  --metrics 0.0.0.0:6060 \
  --log.file.directory $LOG_DIR --log.file.filter info \
  --trusted-peers $TRUSTED_PEERS   # parsed from static-nodes.json
```

### Running as a validator (batch verification mode)

There is no separate validator service anymore — every node self-verifies L1 batches. The
mode is controlled by `DERIVATION_VERIFY_MODE` (`--derivation.verify-mode`) in the env file:

- `local` (default): rebuild the blob from local L2 blocks and compare versioned hashes
  against L1. No beacon fetch on the happy path.
- `layer1`: pull the L1 beacon blob, decode it, and derive via the engine — equivalent to
  the former validator node.

`L1_BEACON_CHAIN_RPC` is required in **both** modes — the node exits at startup without it.
`local` just doesn't fetch the blob on the happy path; `layer1` fetches it every batch.

`layer1` is what the former validator node did. Two ways to enable it:

- **Validator commands** (kept for backward compatibility): `make run-validator` /
  `make run-hoodi-validator` (or the `-binary` variants) run the single node in `layer1`
  mode. Stop/remove with `make stop-validator` / `make rm-validator` (aliases of
  `make stop-node` / `make rm-node`).
- **Env var:** set `DERIVATION_VERIFY_MODE=layer1` in `.env` / `.env_hoodi`, then `make run-node`.

There is no separate validator container anymore — both paths run the same `morph-node`.

> `L1_SEQUENCER_CONTRACT` and `CONSENSUS_SWITCH_HEIGHT` are hardcoded per-network defaults
> in the binary and must not be set as operator config.

## Snapshot Information

The table below provides the node snapshot data and corresponding download URLs. Ensure `DERIVATION_START_HEIGHT`, `L1_MSG_START_HEIGHT`, and `L2_BASE_HEIGHT` in `.env`/`.env_hoodi` match the selected snapshot.

> **geth vs reth snapshots:** rows whose name contains `reth` (e.g. `snapshot-archive-reth-*`)
> are for the **reth** execution client and must be used with the `*-reth-*` make targets;
> the other rows are **geth** snapshots. The two are not interchangeable. Set
> `MAINNET_SNAPSHOT_NAME`/`HOODI_SNAPSHOT_NAME` for geth and
> `MAINNET_RETH_SNAPSHOT_NAME`/`HOODI_RETH_SNAPSHOT_NAME` for reth in the env files.
>
> Because the two clients use different snapshots, the height variables are also split:
> the geth path uses `DERIVATION_START_HEIGHT`/`L1_MSG_START_HEIGHT`/`L2_BASE_HEIGHT`, and
> the reth path uses `RETH_DERIVATION_START_HEIGHT`/`RETH_L1_MSG_START_HEIGHT`/`RETH_L2_BASE_HEIGHT`.
> Ensure each set matches the height row of its selected snapshot.

**For mainnet** (reth is currently in an internal testing phase and is not yet recommended for production use):

| Snapshot Name                                                                         | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:--------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [snapshot-archive-20260902-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260902-1.tar.gz) | 25885664 | 25880870 | 26137782 |
| [snapshot-20260902-1](https://snapshot.morphl2.io/mainnet/snapshot-20260902-1.tar.gz) | 25885664 | 25880870 | 26137782 |
| [snapshot-archive-reth-20260902-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260902-1.tar.gz) | 25885664 | 25880870 | 26137782 |
| [snapshot-archive-20260817-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260817-1.tar.gz) | 25770865 | 25751519 | 25380612 |
| [snapshot-20260817-1](https://snapshot.morphl2.io/mainnet/snapshot-20260817-1.tar.gz) | 25770865 | 25751519 | 25380612 |
| [snapshot-archive-reth-20260817-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260817-1.tar.gz) | 25770865 | 25751519 | 25380612 |
| [snapshot-archive-20260803-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260803-1.tar.gz) | 25671158 | 25658857 | 24979932 |
| [snapshot-20260803-1](https://snapshot.morphl2.io/mainnet/snapshot-20260803-1.tar.gz) | 25671158 | 25658857 | 24980065 |
| [snapshot-archive-reth-20260803-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260803-1.tar.gz) | 25671367 | 25658857 | 24980107 |

**For hoodi testnet** (reth is currently in an internal testing phase and is not yet recommended for production use):

| Snapshot Name                                                                       | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [snapshot-archive-20260901-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260901-1.tar.gz) | 3533250 | 3529538 | 8346379 |
| [snapshot-20260901-1](https://snapshot.morphl2.io/hoodi/snapshot-20260901-1.tar.gz) | 3533250 | 3529538 | 8346379 |
| [snapshot-archive-reth-20260901-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260901-1.tar.gz) | 3533250 | 3529538 | 8346700 |
| [snapshot-archive-20260815-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260815-1.tar.gz) | 3420448 | 3413824 | 7593270 |
| [snapshot-archive-reth-20260815-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260815-1.tar.gz) | 3420448 | 3413824 | 7593270 |
| [snapshot-archive-20260801-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260801-1.tar.gz) | 3327231 | 3316267 | 7223425 |
| [snapshot-20260801-1](https://snapshot.morphl2.io/hoodi/snapshot-20260801-1.tar.gz) | 3327231 | 3316267 | 7223425 |
| [snapshot-archive-reth-20260801-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260801-1.tar.gz) | 3327231 | 3316267 | 7223425 |
| [snapshot-archive-20260722-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260722-1.tar.gz) | 3261967 | 3256524 | 7031698 |

## Verifying Snapshot Integrity

Each snapshot has a SHA-256 checksum file at the same URL with a `.sha256`
suffix. Compute the hash and compare it against the `.sha256` file — use
whichever command is available on your system:

```bash
shasum -a 256 snapshot.tar.gz
# or
openssl dgst -sha256 snapshot.tar.gz
```

## Documentation
For detailed information on Morph and its ecosystem, refer to the official documentation:

- [Morph Documentation](https://morphl2.io)

By following these steps, you can set up and run a Morph node efficiently using Docker. For any questions or support, please refer to the official Morph community channels.








