# run-morph-node

`run-morph-node` is a repository designed to facilitate the deployment and management of Morph nodes using Docker. Morph is an innovative platform that enhances Ethereum Layer 2 scalability by combining optimistic rollups and zk technology, aiming to revolutionize consumer blockchain applications.

## Features

- **Dockerized Deployment**: Simplifies the process of setting up Morph nodes using Docker containers.
- **Network Support**: Provides configurations for both Mainnet and Hoodi testnet environments.
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

**For mainnet** (reth is currently in an internal testing phase and is not yet recommended for production use):

| Snapshot Name                                                                         | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:--------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [snapshot-archive-20260720-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260720-1.tar.gz) | 25572052 | 25553778 | 24664547 |
| [snapshot-20260720-1](https://snapshot.morphl2.io/mainnet/snapshot-20260720-1.tar.gz) | 25572052 | 25553778 | 24664686 |
| [snapshot-archive-reth-20260720-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260720-1.tar.gz) | 25572052 | 25553778 | 24664700 |
| [snapshot-archive-20260701-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260701-1.tar.gz) | 25440822 | 25439950 | 24216219 |
| [snapshot-20260701-1](https://snapshot.morphl2.io/mainnet/snapshot-20260701-1.tar.gz) | 25440822 | 25439950 | 24216219 |
| [snapshot-archive-reth-20260701-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260701-1.tar.gz) | 25440822 | 25439950 | 24216219 |
| [snapshot-archive-20260616-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-20260616-1.tar.gz) | 25333309 | 25330305 | 23832071 |
| [snapshot-20260616-1](https://snapshot.morphl2.io/mainnet/snapshot-20260616-1.tar.gz) | 25333309 | 25330305 | 23832071 |
| [snapshot-archive-reth-20260616-1](https://snapshot.morphl2.io/mainnet/snapshot-archive-reth-20260616-1.tar.gz) | 25333309 | 25330305 | 23832071 |

**For hoodi testnet** (reth is currently in an internal testing phase and is not yet recommended for production use):

| Snapshot Name                                                                       | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [snapshot-archive-reth-20260722-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260722-1.tar.gz) | 3262143 | 3256524 | 7032291 |
| [snapshot-20260722-1](https://snapshot.morphl2.io/hoodi/snapshot-20260722-1.tar.gz) | 3262787 | 3256524 | 7033975 |
| [snapshot-archive-20260714-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260714-1.tar.gz) | 3215887 | 3212415 | 6873482 |
| [snapshot-20260714-1](https://snapshot.morphl2.io/hoodi/snapshot-20260714-1.tar.gz) | 3215887 | 3212415 | 6873482 |
| [snapshot-archive-reth-20260714-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260714-1.tar.gz) | 3215887 | 3212415 | 6873482 |
| [snapshot-archive-20260630-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260630-1.tar.gz) | 3122685 | 3106743 | 6543334 |
| [snapshot-20260630-1](https://snapshot.morphl2.io/hoodi/snapshot-20260630-1.tar.gz) | 3122685 | 3106743 | 6543334 |
| [snapshot-archive-reth-20260630-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260630-1.tar.gz) | 3122685 | 3106743 | 6543334 |
| [snapshot-archive-20260614-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-20260614-1.tar.gz) | 3017861 | 2946604 | 6156574 |
| [snapshot-20260614-1](https://snapshot.morphl2.io/hoodi/snapshot-20260614-1.tar.gz) | 3017861 | 2946604 | 6156574 |
| [snapshot-archive-reth-20260614-1](https://snapshot.morphl2.io/hoodi/snapshot-archive-reth-20260614-1.tar.gz) | 3017861 | 2946604 | 6156574 |

## Documentation
For detailed information on Morph and its ecosystem, refer to the official documentation:

- [Morph Documentation](https://morphl2.io)

By following these steps, you can set up and run a Morph node efficiently using Docker. For any questions or support, please refer to the official Morph community channels.








