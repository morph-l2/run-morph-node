#!/bin/sh

GETH_BIN=${GETH_BINARY:-geth}
GETH_DATADIR=${GETH_DATADIR:-./db}
JWT_PATH=${JWT_SECRET_PATH:-/jwt-secret.txt}

if [ ! -f "${JWT_PATH}" ]; then
    echo "Error: jwt-secret.txt not found at ${JWT_PATH}."
    echo "Please create it before starting the service."
    exit 1
fi

MORPH_FLAG=${MORPH_FLAG:-"morph"}

exec "${GETH_BIN}" \
  "--${MORPH_FLAG}" \
  --morph-mpt \
  "--datadir=${GETH_DATADIR}" \
  --verbosity=3 \
  --http \
  "--http.corsdomain=*" \
  "--http.vhosts=*" \
  --http.addr=0.0.0.0 \
  --http.port=8545 \
  --http.api=web3,debug,eth,txpool,net,morph,engine,admin \
  --ws \
  --ws.addr=0.0.0.0 \
  --ws.port=8546 \
  "--ws.origins=*" \
  --ws.api=web3,debug,eth,txpool,net,morph,engine,admin \
  --authrpc.addr=0.0.0.0 \
  --authrpc.port=8551 \
  "--authrpc.vhosts=*" \
  "--authrpc.jwtsecret=${JWT_PATH}" \
  --gcmode=archive \
  "--log.filename=${GETH_DATADIR}/geth.log" \
  --metrics \
  --metrics.addr=0.0.0.0
