#!/bin/sh

# Usage: run-binary.sh <mode> <env-file> [override-env-file]
#   mode: node | validator
#   env-file: .env | .env_hoodi
#   override-env-file: optional, e.g. .env_zk for ZK legacy mode

MODE=${1:-node}
ENV_FILE=${2:-.env}
OVERRIDE_ENV_FILE=${3:-}

# Source environment
set -a
. ./${ENV_FILE}
if [ -n "${OVERRIDE_ENV_FILE}" ]; then
    . ./${OVERRIDE_ENV_FILE}
fi
set +a

GETH_BINARY=${GETH_BINARY:-./bin/geth}
NODE_BINARY=${NODE_BINARY:-./bin/morphnode}

# Check binaries
if [ ! -f "${GETH_BINARY}" ]; then
    echo "Error: geth binary not found at ${GETH_BINARY}"
    echo "Please download and place it in the bin/ directory."
    exit 1
fi

if [ ! -f "${NODE_BINARY}" ]; then
    echo "Error: morphnode binary not found at ${NODE_BINARY}"
    echo "Please download and place it in the bin/ directory."
    exit 1
fi

# Ensure data directories exist
mkdir -p "${MORPH_HOME}/geth-data"
mkdir -p "${MORPH_HOME}/node-data"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping..."
    [ -n "${GETH_PID:-}" ] && kill ${GETH_PID} 2>/dev/null
    [ -n "${NODE_PID:-}" ] && kill ${NODE_PID} 2>/dev/null
    rm -f .geth.pid .node.pid
    exit
}
trap cleanup INT TERM

# Validate entrypoint file
case "${GETH_ENTRYPOINT_FILE}" in
    ./entrypoint-geth.sh|./entrypoint-geth-zk.sh) ;;
    *)
        echo "Error: invalid GETH_ENTRYPOINT_FILE: ${GETH_ENTRYPOINT_FILE}"
        exit 1
        ;;
esac

# Start geth
echo "Starting geth..."
GETH_BINARY=${GETH_BINARY} \
GETH_DATADIR=${MORPH_HOME}/geth-data \
JWT_SECRET_PATH=${JWT_SECRET_FILE} \
MORPH_FLAG=${MORPH_FLAG} \
sh ./${GETH_ENTRYPOINT_FILE} &
GETH_PID=$!
echo "${GETH_PID}" > .geth.pid

# Wait for geth engine RPC (port 8551)
echo "Waiting for geth to be ready..."
for i in $(seq 1 30); do
    if nc -z localhost 8551 2>/dev/null; then
        echo "Geth is ready."
        break
    fi
    if ! kill -0 ${GETH_PID} 2>/dev/null; then
        echo "Error: geth process exited unexpectedly."
        rm -f .geth.pid
        exit 1
    fi
    sleep 1
done

if ! nc -z localhost 8551 2>/dev/null; then
    echo "Error: geth did not become ready within 30 seconds."
    cleanup
    exit 1
fi

# Set validator mode
if [ "${MODE}" = "validator" ]; then
    NODE_EXTRA_FLAGS="--validator ${NODE_EXTRA_FLAGS:-}"
fi

# Start morphnode
echo "Starting morphnode (${MODE} mode)..."
NODE_BINARY=${NODE_BINARY} \
NODE_HOME=${MORPH_HOME}/node-data \
JWT_SECRET_PATH=${JWT_SECRET_FILE} \
NODE_EXTRA_FLAGS="${NODE_EXTRA_FLAGS:-}" \
sh ./entrypoint-node.sh &
NODE_PID=$!
echo "${NODE_PID}" > .node.pid

echo ""
echo "========================================="
echo "  geth PID:      ${GETH_PID}"
echo "  morphnode PID: ${NODE_PID}"
echo "  geth log:      ${MORPH_HOME}/geth-data/geth.log"
echo "  node log:      ${MORPH_HOME}/node-data/node.log"
echo "========================================="
echo "Press Ctrl+C to stop both processes."
echo ""

wait
