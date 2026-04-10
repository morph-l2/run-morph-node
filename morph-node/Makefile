include .env

# Capture mainnet JWT path before .env_hoodi overwrites MORPH_HOME (:= forces immediate expansion)
JWT_SECRET_FILE_MAINNET := $(JWT_SECRET_FILE)

include .env_hoodi

JWT_SECRET_FILE_HOODI := $(JWT_SECRET_FILE)

generate-jwt:
	@[ -f $(JWT_SECRET_FILE_MAINNET) ] || (echo "Generating $(JWT_SECRET_FILE_MAINNET)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_MAINNET) && echo "$(JWT_SECRET_FILE_MAINNET) created.")

generate-jwt-hoodi:
	@[ -f $(JWT_SECRET_FILE_HOODI) ] || (echo "Generating $(JWT_SECRET_FILE_HOODI)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_HOODI) && echo "$(JWT_SECRET_FILE_HOODI) created.")

## node management
run-node: generate-jwt
	@echo "You are about to run a Mainnet MPT node."
	@echo "To run a ZK (legacy) node instead, use: make run-zk-node"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env up node &

run-hoodi-node: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT node."
	@echo "To run a ZK (legacy) node instead, use: make run-hoodi-zk-node"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env_hoodi up node &


run-zk-node: generate-jwt
	docker-compose --env-file .env --env-file .env_zk up node &

run-hoodi-zk-node: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi --env-file .env_hoodi_zk up node &

stop-node:
	docker stop morph-node morph-geth

rm-node:
	docker rm morph-node morph-geth

## validator management
run-validator: generate-jwt
	@echo "You are about to run a Mainnet MPT validator."
	@echo "To run a ZK (legacy) validator instead, use: make run-zk-validator"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env up validator &

run-hoodi-validator: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT validator."
	@echo "To run a ZK (legacy) validator instead, use: make run-hoodi-zk-validator"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env_hoodi up validator &


run-zk-validator: generate-jwt
	docker-compose --env-file .env --env-file .env_zk up validator &

run-hoodi-zk-validator: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi --env-file .env_hoodi_zk up validator &

stop-validator:
	docker stop validator_node morph-geth

rm-validator:
	docker rm validator_node morph-geth

## build from source (requires Go)
submodule-init:
	@echo "Initializing git submodules..."
	cd .. && git submodule update --init --recursive
	@echo "Submodules ready."

# Update submodule versions and docker-compose.yml image tags in one shot.
# Usage: make set-versions GETH_VERSION=2.2.1 NODE_VERSION=0.5.3
set-versions:
	cd ../go-ethereum && git fetch --tags && git checkout morph-v$(GETH_VERSION)
	cd ../morph       && git fetch --tags && git checkout v$(NODE_VERSION)
	sed -i'' 's|go-ethereum:[0-9.]*|go-ethereum:$(GETH_VERSION)|g' docker-compose.yml
	sed -i'' 's|morph-l2/node:[0-9.]*|morph-l2/node:$(NODE_VERSION)|g' docker-compose.yml
	cd .. && git add go-ethereum morph
	@echo "Done. Commit with: git commit -m 'chore: bump geth=$(GETH_VERSION) node=$(NODE_VERSION)'"

build-geth: submodule-init
	@if [ -f ./bin/geth ]; then \
		echo "geth binary already exists at ./bin/geth, skipping build."; \
	else \
		echo "Building geth from source..."; \
		cd ../go-ethereum && make geth; \
		cp ../go-ethereum/build/bin/geth ./bin/geth; \
		echo "geth binary copied to morph-node/bin/geth"; \
	fi

build-morphnode: submodule-init
	@if [ -f ./bin/morphnode ]; then \
		echo "morphnode binary already exists at ./bin/morphnode, skipping build."; \
	else \
		echo "Building morphnode from source..."; \
		cd ../morph/node && make morphnode; \
		cp ../morph/node/build/bin/morphnode ./bin/morphnode; \
		echo "morphnode binary copied to morph-node/bin/morphnode"; \
	fi

build: build-geth build-morphnode
	@echo "All binaries built successfully."

## binary mode
run-node-binary: generate-jwt
	@echo "You are about to run a Mainnet MPT node (binary mode)."
	@echo "To run a ZK (legacy) node instead, use: make run-zk-node-binary"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh node .env

run-hoodi-node-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT node (binary mode)."
	@echo "To run a ZK (legacy) node instead, use: make run-hoodi-zk-node-binary"
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh node .env_hoodi

run-validator-binary: generate-jwt
	@echo "You are about to run a Mainnet MPT validator (binary mode)."
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh validator .env

run-hoodi-validator-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT validator (binary mode)."
	@printf "Continue? [Y/n] "; read confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh validator .env_hoodi

run-zk-node-binary: generate-jwt
	sh ./run-binary.sh node .env .env_zk

run-hoodi-zk-node-binary: generate-jwt-hoodi
	sh ./run-binary.sh node .env_hoodi .env_hoodi_zk

run-zk-validator-binary: generate-jwt
	sh ./run-binary.sh validator .env .env_zk

run-hoodi-zk-validator-binary: generate-jwt-hoodi
	sh ./run-binary.sh validator .env_hoodi .env_hoodi_zk

stop-binary:
	@if [ -f .geth.pid ]; then kill $$(cat .geth.pid) 2>/dev/null; rm -f .geth.pid; echo "geth stopped."; fi
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

## quickstart targets (one-command setup and run)

quickstart-hoodi-node: generate-jwt-hoodi
	@echo "=== Quickstart: Hoodi Node (Docker) ==="
	$(call setup-snapshot-data,$(HOODI_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	docker-compose --env-file .env_hoodi up node

quickstart-hoodi-node-binary: generate-jwt-hoodi build
	@echo "=== Quickstart: Hoodi Node (Binary) ==="
	$(call setup-snapshot-data,$(HOODI_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi,../hoodi)
	sh ./run-binary.sh node .env_hoodi

quickstart-mainnet-node: generate-jwt
	@echo "=== Quickstart: Mainnet Node (Docker) ==="
	$(call setup-snapshot-data,$(MAINNET_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	docker-compose --env-file .env up node

quickstart-mainnet-node-binary: generate-jwt build
	@echo "=== Quickstart: Mainnet Node (Binary) ==="
	$(call setup-snapshot-data,$(MAINNET_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet,../mainnet)
	sh ./run-binary.sh node .env


# Common function for download and decompress
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
	echo "Downloading $(1).tar.gz from $(2)..."; \
	if wget -O $(1).tar.gz $(2)/$(1).tar.gz; then \
		echo "$(1).tar.gz downloaded successfully."; \
	else \
		echo "Error downloading $(1).tar.gz."; \
		exit 1; \
	fi; \
	echo "Decompressing $(1).tar.gz..."; \
	if tar -xzvf $(1).tar.gz; then \
		echo "$(1).tar.gz decompressed successfully."; \
	else \
		echo "Error decompressing $(1).tar.gz."; \
		exit 1; \
	fi; \
	rm -rf $(1).tar.gz;
endef

# Targets

download-and-decompress-mainnet-snapshot:
	$(call download-and-decompress,$(MAINNET_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)

download-and-decompress-hoodi-snapshot:
	$(call download-and-decompress,$(HOODI_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)

download-and-decompress-mainnet-zk-snapshot:
	$(call download-and-decompress,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)

download-and-decompress-hoodi-zk-snapshot:
	$(call download-and-decompress,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)



