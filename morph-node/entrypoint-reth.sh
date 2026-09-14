#!/bin/sh

# Reth execution-client entrypoint. Mirrors entrypoint-geth.sh but launches
# morph-reth instead of geth. The two clients use DIFFERENT snapshots (see the
# README snapshot table): reth snapshots pack a reth-data/ tree (db, static_files,
# rocksdb, morph), whereas geth snapshots pack a geth/ chaindata tree.

RETH_BIN=${RETH_BINARY:-morph-reth}
RETH_DATADIR=${RETH_DATADIR:-./db}
JWT_PATH=${JWT_SECRET_PATH:-/jwt-secret.txt}
# mainnet | hoodi (selects the built-in chain spec).
RETH_CHAIN=${RETH_CHAIN:-mainnet}
# Directory reth writes its rotating log file into.
LOG_DIR=${LOG_DIR:-${RETH_DATADIR}}
# static-nodes.json (JSON array of enode URLs). Its entries are joined with commas
# and passed to --trusted-peers so reth dials the Morph boot nodes directly
# (discovery is disabled below).
STATIC_NODES_FILE=${STATIC_NODES_FILE:-}

if [ ! -f "${JWT_PATH}" ]; then
    echo "Error: jwt-secret.txt not found at ${JWT_PATH}."
    echo "Please create it before starting the service."
    exit 1
fi

mkdir -p "${LOG_DIR}"

# Parse static-nodes.json (a JSON array of "enode://..." strings) into a single
# comma-separated list for --trusted-peers. No jq dependency: strip everything
# that isn't part of an enode URL, then squeeze the newlines into commas.
TRUSTED_PEERS=""
if [ -n "${STATIC_NODES_FILE}" ] && [ -f "${STATIC_NODES_FILE}" ]; then
    TRUSTED_PEERS=$(grep -o 'enode://[^"]*' "${STATIC_NODES_FILE}" | paste -sd, -)
fi

set -- "${RETH_BIN}" node \
  --chain "${RETH_CHAIN}" \
  --datadir "${RETH_DATADIR}" \
  --http \
  --http.addr 0.0.0.0 \
  --http.port 8545 \
  --http.corsdomain '*' \
  --http.api web3,eth,txpool,net,trace \
  --ws \
  --ws.addr 0.0.0.0 \
  --ws.port 8546 \
  --ws.origins '*' \
  --ws.api web3,eth,txpool,net,trace \
  --authrpc.addr 0.0.0.0 \
  --authrpc.port 8551 \
  --authrpc.jwtsecret "${JWT_PATH}" \
  --disable-discovery \
  --nat none \
  --metrics 0.0.0.0:6060 \
  --log.file.directory "${LOG_DIR}" \
  --log.file.filter info

# Only append --trusted-peers when we actually resolved some, so an empty/missing
# static-nodes.json doesn't hand reth a bare flag with no value.
if [ -n "${TRUSTED_PEERS}" ]; then
    set -- "$@" --trusted-peers "${TRUSTED_PEERS}"
fi

exec "$@"
