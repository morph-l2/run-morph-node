#!/bin/sh

NODE_BIN=${NODE_BINARY:-morphnode}
NODE_HOME=${NODE_HOME:-/db}
JWT_PATH=${JWT_SECRET_PATH:-/jwt-secret.txt}

# L2 connection defaults (localhost for binary mode; Docker overrides via environment section)
export MORPH_NODE_L2_ETH_RPC=${MORPH_NODE_L2_ETH_RPC:-http://localhost:8545}
export MORPH_NODE_L2_ENGINE_RPC=${MORPH_NODE_L2_ENGINE_RPC:-http://localhost:8551}
export MORPH_NODE_L2_ENGINE_AUTH=${MORPH_NODE_L2_ENGINE_AUTH:-${JWT_PATH}}

# Map .env variables to MORPH_NODE_* for binary mode (Docker sets these directly)
export MORPH_NODE_L1_ETH_RPC=${MORPH_NODE_L1_ETH_RPC:-${L1_ETH_RPC:-}}
export MORPH_NODE_ROLLUP_ADDRESS=${MORPH_NODE_ROLLUP_ADDRESS:-${ROLLUP_CONTRACT:-}}

# Map remaining .env variables to MORPH_NODE_* for binary mode (Docker sets these directly)
export MORPH_NODE_L1_ETH_BEACON_RPC=${MORPH_NODE_L1_ETH_BEACON_RPC:-${L1_BEACON_CHAIN_RPC:-}}
export MORPH_NODE_SYNC_DEPOSIT_CONTRACT_ADDRESS=${MORPH_NODE_SYNC_DEPOSIT_CONTRACT_ADDRESS:-${L1MESSAGEQUEUE_CONTRACT:-}}
DERIVATION_START_HEIGHT_VALUE=${MORPH_NODE_DERIVATION_START_HEIGHT:-${DERIVATION_START_HEIGHT:-}}
if [ -n "${DERIVATION_START_HEIGHT_VALUE}" ]; then
  export MORPH_NODE_DERIVATION_START_HEIGHT="${DERIVATION_START_HEIGHT_VALUE}"
fi

DERIVATION_BASE_HEIGHT_VALUE=${MORPH_NODE_DERIVATION_BASE_HEIGHT:-${L2_BASE_HEIGHT:-}}
if [ -n "${DERIVATION_BASE_HEIGHT_VALUE}" ]; then
  export MORPH_NODE_DERIVATION_BASE_HEIGHT="${DERIVATION_BASE_HEIGHT_VALUE}"
fi

export MORPH_NODE_SYNC_START_HEIGHT=${MORPH_NODE_SYNC_START_HEIGHT:-${L1_MSG_START_HEIGHT:-}}
export MORPH_NODE_L1_CHAIN_ID=${MORPH_NODE_L1_CHAIN_ID:-${L1_CHAIN_ID:-}}

# Batch verification mode (--derivation.verify-mode). "local" (default) rebuilds
# the blob from local L2 and compares versioned hashes vs L1; "layer1" pulls the
# L1 beacon blob and derives via the engine (former validator behavior).
# Export only when set; empty/unset falls back to the binary default (local).
DERIVATION_VERIFY_MODE_VALUE=${MORPH_NODE_DERIVATION_VERIFY_MODE:-${DERIVATION_VERIFY_MODE:-}}
if [ -n "${DERIVATION_VERIFY_MODE_VALUE}" ]; then
  export MORPH_NODE_DERIVATION_VERIFY_MODE="${DERIVATION_VERIFY_MODE_VALUE}"
else
  unset MORPH_NODE_DERIVATION_VERIFY_MODE
fi

COMMAND="${NODE_BIN} \
--home ${NODE_HOME} \
--log.filename ${NODE_HOME}/node.log \
${NODE_EXTRA_FLAGS:-}"

eval $COMMAND
