include .env

# Capture mainnet JWT path before .env_hoodi overwrites MORPH_HOME (:= forces immediate expansion)
JWT_SECRET_FILE_MAINNET := $(JWT_SECRET_FILE)
# Capture mainnet reth snapshot name for the same reason.
MAINNET_RETH_SNAPSHOT_NAME := $(MAINNET_RETH_SNAPSHOT_NAME)

include .env_hoodi

JWT_SECRET_FILE_HOODI := $(JWT_SECRET_FILE)

# morph-reth version to build/run. Keep this in sync with the image tag in
# docker-compose.reth.yml (v$(RETH_VERSION)). Override on the command line, e.g.
# `make build-reth RETH_VERSION=1.4.0`. `?=` lets an env var take precedence.
RETH_VERSION ?= 1.3.0

generate-jwt:
	@[ -f $(JWT_SECRET_FILE_MAINNET) ] || (echo "Generating $(JWT_SECRET_FILE_MAINNET)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_MAINNET) && echo "$(JWT_SECRET_FILE_MAINNET) created.")

generate-jwt-hoodi:
	@[ -f $(JWT_SECRET_FILE_HOODI) ] || (echo "Generating $(JWT_SECRET_FILE_HOODI)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_HOODI) && echo "$(JWT_SECRET_FILE_HOODI) created.")

## node management
run-node: generate-jwt
	@echo "You are about to run a Mainnet node."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	docker-compose --env-file .env up node &

run-hoodi-node: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	docker-compose --env-file .env_hoodi up node &

stop-node:
	docker stop morph-node morph-geth

rm-node:
	docker rm morph-node morph-geth

## reth node management (reth is an alternative execution client to geth; it uses
## a SEPARATE snapshot — see the README snapshot table — and its own reth-data dir).
run-reth-node: generate-jwt
	@echo "You are about to run a Mainnet node with the reth execution client."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	docker-compose -f docker-compose.reth.yml --env-file .env up node &

run-hoodi-reth-node: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node with the reth execution client."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	docker-compose -f docker-compose.reth.yml --env-file .env_hoodi up node &

stop-reth-node:
	docker stop morph-node morph-reth

rm-reth-node:
	docker rm morph-node morph-reth

## Validator commands, kept for backward compatibility. A "validator" is now just
## the single node run in layer1 batch-verification mode (--derivation.verify-mode=layer1:
## pull the L1 beacon blob and derive via the engine). There is no separate validator
## container anymore, so stop/rm operate on the same morph-node container.
## Requires a working L1_BEACON_CHAIN_RPC in the env file.
run-validator: generate-jwt
	@echo "You are about to run a Mainnet node in validator mode (--derivation.verify-mode=layer1)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	DERIVATION_VERIFY_MODE=layer1 docker-compose --env-file .env up node &

run-hoodi-validator: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node in validator mode (--derivation.verify-mode=layer1)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	DERIVATION_VERIFY_MODE=layer1 docker-compose --env-file .env_hoodi up node &

## Backward-compat aliases: the validator is now the same container as the node.
stop-validator: stop-node

rm-validator: rm-node

## build from source (requires Go)
submodule-init:
	@echo "Initializing git submodules..."
	cd .. && git submodule update --init --recursive
	@echo "Submodules ready."

# Update submodule versions and docker-compose.yml image tags in one shot.
# Usage: make set-versions GETH_VERSION=2.2.1 NODE_VERSION=0.5.3 [RETH_VERSION=1.4.0]
# RETH_VERSION also rewrites the morph-reth image tag in docker-compose.reth.yml so
# the Docker and binary reth paths stay on the same version (defaults to $(RETH_VERSION)).
set-versions:
	cd ../go-ethereum && git fetch --tags && git checkout morph-v$(GETH_VERSION)
	cd ../morph       && git fetch --tags && git checkout v$(NODE_VERSION)
	sed -i'' 's|go-ethereum:[0-9.]*|go-ethereum:$(GETH_VERSION)|g' docker-compose.yml
	sed -i'' 's|morph-l2/node:[0-9.]*|morph-l2/node:$(NODE_VERSION)|g' docker-compose.yml
	sed -i'' 's|morph-reth:v[0-9.]*|morph-reth:v$(RETH_VERSION)|g' docker-compose.reth.yml
	cd .. && git add go-ethereum morph
	@echo "Done. Commit with: git commit -m 'chore: bump geth=$(GETH_VERSION) node=$(NODE_VERSION) reth=$(RETH_VERSION)'"

build-geth: submodule-init
	@if [ -f ./bin/geth ]; then \
		echo "geth binary already exists at ./bin/geth, skipping build."; \
	else \
		echo "Building geth from source..."; \
		(cd ../go-ethereum && make geth) || { echo "Error: geth build failed."; exit 1; }; \
		mkdir -p ./bin; \
		cp ../go-ethereum/build/bin/geth ./bin/geth || { echo "Error: failed to copy geth binary to morph-node/bin/geth."; exit 1; }; \
		echo "geth binary copied to morph-node/bin/geth"; \
	fi

build-morphnode: submodule-init
	@if [ -f ./bin/morphnode ]; then \
		echo "morphnode binary already exists at ./bin/morphnode, skipping build."; \
	else \
		echo "Building morphnode from source..."; \
		(cd ../morph/node && make morphnode) || { echo "Error: morphnode build failed."; exit 1; }; \
		mkdir -p ./bin; \
		cp ../morph/node/build/bin/morphnode ./bin/morphnode || { echo "Error: failed to copy morphnode binary to morph-node/bin/morphnode."; exit 1; }; \
		echo "morphnode binary copied to morph-node/bin/morphnode"; \
	fi

## Build morph-reth from source (requires the Rust toolchain / cargo). morph-reth
## lives in its own repo (https://github.com/morph-l2/morph-reth), not a submodule,
## so we clone it under ../morph-reth on first build.
build-reth:
	@if [ -f ./bin/morph-reth ]; then \
		echo "morph-reth binary already exists at ./bin/morph-reth, skipping build."; \
	else \
		echo "Building morph-reth v$(RETH_VERSION) from source..."; \
		if [ ! -d ../morph-reth ]; then \
			echo "Cloning morph-reth..."; \
			git clone https://github.com/morph-l2/morph-reth.git ../morph-reth || { echo "Error: failed to clone morph-reth."; exit 1; }; \
		fi; \
		echo "Checking out v$(RETH_VERSION) (pinned to match docker-compose.reth.yml)..."; \
		(cd ../morph-reth && git fetch --tags && git checkout v$(RETH_VERSION)) || { echo "Error: failed to checkout morph-reth v$(RETH_VERSION)."; exit 1; }; \
		(cd ../morph-reth && cargo build --release) || { echo "Error: morph-reth build failed."; exit 1; }; \
		mkdir -p ./bin; \
		cp ../morph-reth/target/release/morph-reth ./bin/morph-reth || { echo "Error: failed to copy morph-reth binary to morph-node/bin/morph-reth."; exit 1; }; \
		echo "morph-reth binary copied to morph-node/bin/morph-reth"; \
	fi

build: build-geth build-morphnode
	@echo "All binaries built successfully."

## Build the reth-based binary set (reth + morphnode).
build-reth-all: build-reth build-morphnode
	@echo "All reth binaries built successfully."

## binary mode
run-node-binary: generate-jwt
	@echo "You are about to run a Mainnet node (binary mode)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	sh ./run-binary.sh .env

run-hoodi-node-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node (binary mode)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	sh ./run-binary.sh .env_hoodi

## Validator commands (binary), kept for backward compatibility = single node with
## --derivation.verify-mode=layer1. MORPH_NODE_DERIVATION_VERIFY_MODE is not set by
## the env files, so it survives sourcing and the entrypoint honors it first.
## Requires L1_BEACON_CHAIN_RPC.
run-validator-binary: generate-jwt
	@echo "You are about to run a Mainnet node in validator mode (--derivation.verify-mode=layer1, binary)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	MORPH_NODE_DERIVATION_VERIFY_MODE=layer1 sh ./run-binary.sh .env

run-hoodi-validator-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node in validator mode (--derivation.verify-mode=layer1, binary)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	MORPH_NODE_DERIVATION_VERIFY_MODE=layer1 sh ./run-binary.sh .env_hoodi

## reth binary mode
run-reth-node-binary: generate-jwt
	@echo "You are about to run a Mainnet node with reth (binary mode)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	sh ./run-binary-reth.sh .env

run-hoodi-reth-node-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi node with reth (binary mode)."
	@{ [ -t 0 ] || { echo "Error: interactive confirmation required (run in a TTY)."; exit 1; }; printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi; }
	sh ./run-binary-reth.sh .env_hoodi

stop-binary:
	@if [ -f .geth.pid ]; then kill $$(cat .geth.pid) 2>/dev/null; rm -f .geth.pid; echo "geth stopped."; fi
	@if [ -f .reth.pid ]; then kill $$(cat .reth.pid) 2>/dev/null; rm -f .reth.pid; echo "reth stopped."; fi
	@if [ -f .node.pid ]; then kill $$(cat .node.pid) 2>/dev/null; rm -f .node.pid; echo "morphnode stopped."; fi

clean-mainnet-binary:
	@echo "Cleaning mainnet snapshot data (keeping config)..."
	rm -rf ../mainnet/geth-data/geth
	rm -rf ../mainnet/node-data/data/*
	@printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > ../mainnet/node-data/data/priv_validator_state.json
	@echo "Mainnet snapshot data cleaned."

clean-hoodi-binary:
	@echo "Cleaning hoodi snapshot data (keeping config)..."
	rm -rf ../hoodi/geth-data/geth
	rm -rf ../hoodi/node-data/data/*
	@printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > ../hoodi/node-data/data/priv_validator_state.json
	@echo "Hoodi snapshot data cleaned."

clean-mainnet-reth:
	@echo "Cleaning mainnet reth snapshot data (keeping config)..."
	rm -rf ../mainnet/reth-data/db ../mainnet/reth-data/static_files ../mainnet/reth-data/rocksdb ../mainnet/reth-data/morph
	rm -rf ../mainnet/node-data/data/*
	@printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > ../mainnet/node-data/data/priv_validator_state.json
	@echo "Mainnet reth snapshot data cleaned."

clean-hoodi-reth:
	@echo "Cleaning hoodi reth snapshot data (keeping config)..."
	rm -rf ../hoodi/reth-data/db ../hoodi/reth-data/static_files ../hoodi/reth-data/rocksdb ../hoodi/reth-data/morph
	rm -rf ../hoodi/node-data/data/*
	@printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > ../hoodi/node-data/data/priv_validator_state.json
	@echo "Hoodi reth snapshot data cleaned."

# Helper: download, extract, and move snapshot data into MORPH_HOME
# $(1) = snapshot name, $(2) = download URL base, $(3) = MORPH_HOME
define setup-snapshot-data
	@if [ -d "$(3)/geth-data/geth/chaindata" ]; then \
		echo "Snapshot data already in place at $(3), skipping setup."; \
	else \
		echo "Setting up snapshot data for $(3)..."; \
		if [ ! -d "$(3)/$(1)" ]; then \
			if [ ! -f "$(3)/$(1).tar.gz" ]; then \
				echo "Downloading $(1).tar.gz from $(2)..."; \
				wget -O $(3)/$(1).tar.gz $(2)/$(1).tar.gz || { echo "Error: download failed."; exit 1; }; \
			else \
				echo "Found existing $(3)/$(1).tar.gz, skipping download."; \
			fi; \
			echo "Extracting $(1).tar.gz..."; \
			tar -xzf $(3)/$(1).tar.gz -C $(3) || { echo "Error: extraction failed."; exit 1; }; \
			rm -f $(3)/$(1).tar.gz; \
		else \
			echo "Found existing $(3)/$(1)/ directory, skipping download."; \
		fi; \
		mkdir -p $(3)/geth-data $(3)/node-data/data; \
		echo "Moving geth data to $(3)/geth-data/..."; \
		mv $(3)/$(1)/geth $(3)/geth-data/ || { echo "Error: failed to move geth data (may already exist)."; exit 1; }; \
		echo "Moving node data to $(3)/node-data/data/..."; \
		mv $(3)/$(1)/data/* $(3)/node-data/data/ || { echo "Error: failed to move node data."; exit 1; }; \
		rm -rf $(3)/$(1); \
		[ -f "$(3)/node-data/data/priv_validator_state.json" ] || printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > $(3)/node-data/data/priv_validator_state.json; \
		echo "Snapshot data ready at $(3)."; \
	fi
endef

# Helper: download, extract, and move a RETH snapshot into RETH_HOME. Reth snapshots
# pack a different layout than geth: <snapshot>/reth-data/{db,static_files,rocksdb,morph}
# plus <snapshot>/data/* for the node. static-nodes.json is NOT in the snapshot, so we
# copy it from geth-data/ (already tracked in the repo) into reth-data/ for --trusted-peers.
# $(1) = snapshot name, $(2) = download URL base, $(3) = RETH_HOME
define setup-snapshot-data-reth
	@if [ -d "$(3)/reth-data/db" ]; then \
		echo "Reth snapshot data already in place at $(3), skipping setup."; \
	else \
		echo "Setting up reth snapshot data for $(3)..."; \
		if [ ! -d "$(3)/$(1)" ]; then \
			if [ ! -f "$(3)/$(1).tar.gz" ]; then \
				echo "Downloading $(1).tar.gz from $(2)..."; \
				wget -O $(3)/$(1).tar.gz $(2)/$(1).tar.gz || { echo "Error: download failed."; exit 1; }; \
			else \
				echo "Found existing $(3)/$(1).tar.gz, skipping download."; \
			fi; \
			echo "Extracting $(1).tar.gz..."; \
			tar -xzf $(3)/$(1).tar.gz -C $(3) || { echo "Error: extraction failed."; exit 1; }; \
			rm -f $(3)/$(1).tar.gz; \
		else \
			echo "Found existing $(3)/$(1)/ directory, skipping download."; \
		fi; \
		mkdir -p $(3)/reth-data $(3)/node-data/data; \
		echo "Moving reth data to $(3)/reth-data/..."; \
		mv $(3)/$(1)/reth-data/* $(3)/reth-data/ || { echo "Error: failed to move reth data (may already exist)."; exit 1; }; \
		echo "Moving node data to $(3)/node-data/data/..."; \
		mv $(3)/$(1)/data/* $(3)/node-data/data/ || { echo "Error: failed to move node data."; exit 1; }; \
		rm -rf $(3)/$(1); \
		[ -f "$(3)/reth-data/static-nodes.json" ] || cp $(3)/geth-data/static-nodes.json $(3)/reth-data/static-nodes.json 2>/dev/null || echo "Warning: no static-nodes.json found in $(3)/geth-data/; --trusted-peers will be empty."; \
		[ -f "$(3)/node-data/data/priv_validator_state.json" ] || printf '{\n  "height": "0",\n  "round": 0,\n  "step": 0\n}\n' > $(3)/node-data/data/priv_validator_state.json; \
		echo "Reth snapshot data ready at $(3)."; \
	fi
endef

## quickstart targets (one-command setup and run)

quickstart-hoodi-node: generate-jwt-hoodi
	@echo "=== Quickstart: Hoodi Node (Docker) ==="
	$(call setup-snapshot-data,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	docker-compose --env-file .env_hoodi up node

quickstart-hoodi-node-binary: generate-jwt-hoodi build
	@echo "=== Quickstart: Hoodi Node (Binary) ==="
	$(call setup-snapshot-data,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	sh ./run-binary.sh .env_hoodi

quickstart-mainnet-node: generate-jwt
	@echo "=== Quickstart: Mainnet Node (Docker) ==="
	$(call setup-snapshot-data,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	docker-compose --env-file .env up node

quickstart-mainnet-node-binary: generate-jwt build
	@echo "=== Quickstart: Mainnet Node (Binary) ==="
	$(call setup-snapshot-data,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	sh ./run-binary.sh .env

## reth quickstart targets (use the reth snapshot + reth execution client)
quickstart-hoodi-reth-node: generate-jwt-hoodi
	@echo "=== Quickstart: Hoodi Node with reth (Docker) ==="
	$(call setup-snapshot-data-reth,$(HOODI_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	docker-compose -f docker-compose.reth.yml --env-file .env_hoodi up node

quickstart-hoodi-reth-node-binary: generate-jwt-hoodi build-reth-all
	@echo "=== Quickstart: Hoodi Node with reth (Binary) ==="
	$(call setup-snapshot-data-reth,$(HOODI_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	sh ./run-binary-reth.sh .env_hoodi

quickstart-mainnet-reth-node: generate-jwt
	@echo "=== Quickstart: Mainnet Node with reth (Docker) ==="
	$(call setup-snapshot-data-reth,$(MAINNET_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	docker-compose -f docker-compose.reth.yml --env-file .env up node

quickstart-mainnet-reth-node-binary: generate-jwt build-reth-all
	@echo "=== Quickstart: Mainnet Node with reth (Binary) ==="
	$(call setup-snapshot-data-reth,$(MAINNET_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	sh ./run-binary-reth.sh .env


# Common function for download and decompress
# $(1) = snapshot name, $(2) = download URL base, $(3) = target directory
define download-and-decompress
	@echo "Checking for required tools (wget, tar)..."; \
	if ! command -v wget > /dev/null; then \
		echo "Error: wget is not installed."; \
		exit 1; \
	fi; \
	if ! command -v tar > /dev/null; then \
		echo "Error: tar is not installed."; \
		exit 1; \
	fi; \
	echo "Tools are available."; \
	mkdir -p $(3); \
	echo "Downloading $(1).tar.gz from $(2)..."; \
	if wget -O $(3)/$(1).tar.gz $(2)/$(1).tar.gz; then \
		echo "$(1).tar.gz downloaded successfully."; \
	else \
		echo "Error downloading $(1).tar.gz."; \
		exit 1; \
	fi; \
	echo "Decompressing $(1).tar.gz..."; \
	if tar -xzvf $(3)/$(1).tar.gz -C $(3); then \
		echo "$(1).tar.gz decompressed successfully."; \
	else \
		echo "Error decompressing $(1).tar.gz."; \
		exit 1; \
	fi; \
	rm -rf $(3)/$(1).tar.gz;
endef

# Targets

download-and-decompress-mainnet-snapshot:
	$(call download-and-decompress,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)

download-and-decompress-hoodi-snapshot:
	$(call download-and-decompress,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)

## reth snapshots (separate from the geth snapshots above)
download-and-decompress-mainnet-reth-snapshot:
	$(call download-and-decompress,$(MAINNET_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)

download-and-decompress-hoodi-reth-snapshot:
	$(call download-and-decompress,$(HOODI_RETH_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)

# Backward-compatible aliases used in older PR/test plans
download-and-decompress-mainnet-mpt-snapshot: download-and-decompress-mainnet-snapshot

download-and-decompress-hoodi-mpt-snapshot: download-and-decompress-hoodi-snapshot



