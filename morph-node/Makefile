include .env

# Store the value of JWT_SECRET_FILE from .env
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
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env up node &

run-hoodi-node: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT node."
	@echo "To run a ZK (legacy) node instead, use: make run-hoodi-zk-node"
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
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
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env up validator &

run-hoodi-validator: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT validator."
	@echo "To run a ZK (legacy) validator instead, use: make run-hoodi-zk-validator"
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	docker-compose --env-file .env_hoodi up validator &


run-zk-validator: generate-jwt
	docker-compose --env-file .env --env-file .env_zk up validator &

run-hoodi-zk-validator: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi --env-file .env_hoodi_zk up validator &

stop-validator:
	docker stop validator-node morph-geth

rm-validator:
	docker rm validator-node morph-geth

## build from source (requires Go)
submodule-init:
	@echo "Initializing git submodules..."
	cd .. && git submodule update --init --recursive
	@echo "Submodules ready."

build-geth: submodule-init
	@echo "Building geth from source (go-ethereum@morph-v2.2.1)..."
	cd ../go-ethereum && make geth
	cp ../go-ethereum/build/bin/geth ./bin/geth
	@echo "geth binary copied to morph-node/bin/geth"

build-morphnode: submodule-init
	@echo "Building morphnode from source (morph@v0.5.3)..."
	cd ../morph/node && make morphnode
	cp ../morph/node/build/bin/morphnode ./bin/morphnode
	@echo "morphnode binary copied to morph-node/bin/morphnode"

build: build-geth build-morphnode
	@echo "All binaries built successfully."

## binary mode
run-node-binary: generate-jwt
	@echo "You are about to run a Mainnet MPT node (binary mode)."
	@echo "To run a ZK (legacy) node instead, use: make run-zk-node-binary"
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh node .env

run-hoodi-node-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT node (binary mode)."
	@echo "To run a ZK (legacy) node instead, use: make run-hoodi-zk-node-binary"
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh node .env_hoodi

run-validator-binary: generate-jwt
	@echo "You are about to run a Mainnet MPT validator (binary mode)."
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
	sh ./run-binary.sh validator .env

run-hoodi-validator-binary: generate-jwt-hoodi
	@echo "You are about to run a Hoodi MPT validator (binary mode)."
	@read -p "Continue? [Y/n] " confirm; if [ "$$confirm" = "n" ] || [ "$$confirm" = "N" ]; then exit 1; fi
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
	if wget -q --show-progress -O $(1).tar.gz $(2)/$(1).tar.gz; then \
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



