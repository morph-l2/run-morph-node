#!/bin/sh

# Usage: run-binary-reth.sh <env-file> [override-env-file]
#   env-file: .env | .env_hoodi
#   override-env-file: optional extra env file layered on top
#
# Binary-mode launcher for the reth execution client + morphnode. Mirrors
# run-binary.sh but starts morph-reth instead of geth. Reth uses a separate
# snapshot and data dir (${RETH_HOME}/reth-data); node-data is shared.

ENV_FILE=${1:-.env}
OVERRIDE_ENV_FILE=${2:-}

# Source environment
set -a
. ./${ENV_FILE}
if [ -n "${OVERRIDE_ENV_FILE}" ]; then
    . ./${OVERRIDE_ENV_FILE}
fi
set +a

RETH_BINARY=${RETH_BINARY:-./bin/morph-reth}
NODE_BINARY=${NODE_BINARY:-./bin/morphnode}

# Check binaries
if [ ! -f "${RETH_BINARY}" ]; then
    echo "Error: morph-reth binary not found at ${RETH_BINARY}"
    echo "Please build it (make build-reth) or place it in the bin/ directory."
    exit 1
fi

if [ ! -f "${NODE_BINARY}" ]; then
    echo "Error: morphnode binary not found at ${NODE_BINARY}"
    echo "Please download and place it in the bin/ directory."
    exit 1
fi

# Ensure data directories exist
mkdir -p "${RETH_HOME}/reth-data"
mkdir -p "${RETH_HOME}/node-data"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping..."
    [ -n "${RETH_PID:-}" ] && kill ${RETH_PID} 2>/dev/null
    [ -n "${NODE_PID:-}" ] && kill ${NODE_PID} 2>/dev/null
    rm -f .reth.pid .node.pid
    exit
}
trap cleanup INT TERM

# Validate entrypoint file
case "${RETH_ENTRYPOINT_FILE}" in
    ./entrypoint-reth.sh) ;;
    *)
        echo "Error: invalid RETH_ENTRYPOINT_FILE: ${RETH_ENTRYPOINT_FILE}"
        exit 1
        ;;
esac

# Start reth
echo "Starting morph-reth..."
RETH_BINARY=${RETH_BINARY} \
RETH_DATADIR=${RETH_HOME}/reth-data \
LOG_DIR=${RETH_HOME}/reth-data \
JWT_SECRET_PATH=${JWT_SECRET_FILE} \
RETH_CHAIN=${RETH_CHAIN} \
STATIC_NODES_FILE=${RETH_HOME}/reth-data/static-nodes.json \
sh ${RETH_ENTRYPOINT_FILE} &
RETH_PID=$!
echo "${RETH_PID}" > .reth.pid

# Wait for reth engine RPC (port 8551)
echo "Waiting for reth to be ready..."
for i in $(seq 1 30); do
    if nc -z localhost 8551 2>/dev/null; then
        echo "Reth is ready."
        break
    fi
    if ! kill -0 ${RETH_PID} 2>/dev/null; then
        echo "Error: reth process exited unexpectedly."
        rm -f .reth.pid
        exit 1
    fi
    sleep 1
done

if ! nc -z localhost 8551 2>/dev/null; then
    echo "Error: reth did not become ready within 30 seconds."
    cleanup
    exit 1
fi

# Start morphnode
echo "Starting morphnode..."
NODE_BINARY=${NODE_BINARY} \
NODE_HOME=${RETH_HOME}/node-data \
JWT_SECRET_PATH=${JWT_SECRET_FILE} \
NODE_EXTRA_FLAGS="${NODE_EXTRA_FLAGS:-}" \
sh ./entrypoint-node.sh &
NODE_PID=$!
echo "${NODE_PID}" > .node.pid

echo ""
echo "========================================="
echo "  reth PID:      ${RETH_PID}"
echo "  morphnode PID: ${NODE_PID}"
echo "  reth log:      ${RETH_HOME}/reth-data/reth.log"
echo "  node log:      ${RETH_HOME}/node-data/node.log"
echo "========================================="
echo "Press Ctrl+C to stop both processes."
echo ""

wait
