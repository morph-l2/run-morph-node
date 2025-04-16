# run-morph-node

`run-morph-node` is a repository designed to facilitate the deployment and management of Morph nodes using Docker. Morph is an innovative platform that enhances Ethereum Layer 2 scalability by combining optimistic rollups and zk technology, aiming to revolutionize consumer blockchain applications.

## Features

- **Dockerized Deployment**: Simplifies the process of setting up Morph validator nodes using Docker containers.
- **Network Support**: Provides configurations for both Mainnet and Holesky testnet environments.
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

- For Holesky testnet, use the corresponding command:

    ```bash
    make download-and-decompress-holesky-snapshot
    ```

- After downloading the snapshot, you need to manually place the decompressed data files in the appropriate node data directories. 
    - For example, if the snapshot folder is named `snapshot-20250122-1`, move the directory `snapshot-20250122-1/geth` to the `MORPH_HOME/geth-data` directory and the contents from `snapshot-20250122-1/data` to the `${NODE_DATA_DIR}/data directory`.
        ```
        mv ./morph-node/snapshot-20250122-1/geth ${MORPH_HOME}/geth-data
        mv ./morph-node/snapshot-20250122-1/data/* ${MORPH_HOME}/node-data/data
        ```

    - The folder structure will be like
        ```
        └── ${MORPH_HOME}
            ├── geth-data // data directory for geth
            │   └── static-nodes.json
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

    For testnet, run
        
    ```bash
    make run-holesky-node
    ```   

- This command will set up and run the node based on the configurations specified in your .env file.

## Snapshot Information

The table below provides the node snapshot data and corresponding download URLs. When starting the validator, ensure the `DERIVATION_START_HEIGHT` and `L1_MSG_START_HEIGHT` variables defined in the `.env`(or `.env_holesky` if testnet)match the selected snapshot.

**For mainnet**:

|    Snapshot Name    |Derivation Start Height | L1 Msg Start Height |
|:--------------------|:-----------------------|:--------------------|
|[snapshot-20250325-1](https://snapshot.morphl2.io/mainnet/snapshot-20250325-1.tar.gz)|22121099|22119954|
|[snapshot-20250304-1](https://snapshot.morphl2.io/mainnet/snapshot-20250304-1.tar.gz)|21971760|21971689|
|[snapshot-20250205-1](https://snapshot.morphl2.io/mainnet/snapshot-20250205-1.tar.gz)|21779157|21778981|


**For testnet**:

|    Snapshot Name    |Derivation Start Height | L1 Msg Start Height |
|:--------------------|:------------------------|:--------------------|
|[snapshot-20250416-1](https://snapshot.morphl2.io/holesky/snapshot-20250416-1.tar.gz)|3680753|3680413|
|[snapshot-20250331-1](https://snapshot.morphl2.io/holesky/snapshot-20250331-1.tar.gz)|3588874|3588818|
|[snapshot-20250325-1](https://snapshot.morphl2.io/holesky/snapshot-20250325-1.tar.gz)|3553163|3552960|

## Documentation
For detailed information on Morph and its ecosystem, refer to the official documentation:

- [Morph Documentation](https://morphl2.io)

By following these steps, you can set up and run a Morph node efficiently using Docker. For any questions or support, please refer to the official Morph community channels.








