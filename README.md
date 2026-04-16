# run-morph-node

`run-morph-node` is a repository designed to facilitate the deployment and management of Morph nodes using Docker. Morph is an innovative platform that enhances Ethereum Layer 2 scalability by combining optimistic rollups and zk technology, aiming to revolutionize consumer blockchain applications.

## Features

- **Dockerized Deployment**: Simplifies the process of setting up Morph validator nodes using Docker containers.
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

- For ZK node (legacy), download the ZK-specific snapshot:

    ```bash
    make download-and-decompress-mainnet-zk-snapshot
    ```
    or
    ```bash
    make download-and-decompress-hoodi-zk-snapshot
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

- Both commands default to MPT mode. For ZK legacy nodes, use `make run-zk-node` or `make run-hoodi-zk-node`.

- This command will set up and run the node based on the configurations specified in your .env file.

## Snapshot Information

The table below provides the node snapshot data and corresponding download URLs. When starting the validator, ensure `DERIVATION_START_HEIGHT`, `L1_MSG_START_HEIGHT`, and `L2_BASE_HEIGHT` match the selected snapshot: use `.env`/`.env_hoodi` for MPT, and `.env_zk`/`.env_hoodi_zk` for ZK legacy.

**For mainnet**:

| Snapshot Name                                                                         | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:--------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [snapshot-20260415-1](https://snapshot.morphl2.io/mainnet/snapshot-20260415-1.tar.gz) | 24883902 | 24883052 | 22181317 |
| [mpt-snapshot-20260312-1](https://snapshot.morphl2.io/mainnet/mpt-snapshot-20260312-1.tar.gz) | 24639293                | 24637932            | 21382556      |

**For hoodi testnet**:

| Snapshot Name                                                                       | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:------------------------------------------------------------------------------------|:------------------------|:--------------------|:---------------|
| [mpt-snapshot-20260402-1](https://snapshot.morphl2.io/hoodi/mpt-snapshot-20260402-1.tar.gz) | 2534958 | 2528506 | 4391571 |
| [mpt-snapshot-archive-20260401-1](https://snapshot.morphl2.io/hoodi/mpt-snapshot-archive-20260401-1.tar.gz) | 2528394 | 2517091 | 4368142 |
| [mpt-snapshot-archive-20260316-1](https://snapshot.morphl2.io/hoodi/mpt-snapshot-archive-20260316-1.tar.gz) | 2427831 | 2408746 | 4001210 |

**For mainnet ZK node(legacy)**:

| Snapshot Name | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:--------------|:------------------------|:--------------------|:---------------|
| [snapshot-20260316-1](https://snapshot.morphl2.io/mainnet/snapshot-20260316-1.tar.gz) | 24668486                | 24667943            | 21474974      |
| [snapshot-20260304-1](https://snapshot.morphl2.io/mainnet/snapshot-20260304-1.tar.gz) | 24582164                | 24582123            | 21195806      |
| [snapshot-20260210-1](https://snapshot.morphl2.io/mainnet/snapshot-20260210-1.tar.gz) | 24424695                | 24424698            | 20674922      |

**For hoodi testnet ZK node(legacy)**:

| Snapshot Name | Derivation Start Height | L1 Msg Start Height | L2 Base Height |
|:--------------|:------------------------|:--------------------|:---------------|
| [snapshot-20260316-1](https://snapshot.morphl2.io/hoodi/snapshot-20260316-1.tar.gz) | 2427831                 | 2408746             | 4001145        |
| [snapshot-20260304-1](https://snapshot.morphl2.io/hoodi/snapshot-20260304-1.tar.gz) | 2349111                 | 2346416             | 3713448        |
| [snapshot-20260210-1](https://snapshot.morphl2.io/hoodi/snapshot-20260210-1.tar.gz) | 2205636                 | 2201288             | 3187147        |


## Documentation
For detailed information on Morph and its ecosystem, refer to the official documentation:

- [Morph Documentation](https://morphl2.io)

By following these steps, you can set up and run a Morph node efficiently using Docker. For any questions or support, please refer to the official Morph community channels.








