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

run-hoodi-mpt-node: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi up node &

run-mainnet-mpt-node: generate-jwt
	docker-compose --env-file .env up node &

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

run-hoodi-mpt-validator: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi up validator &

run-mainnet-mpt-validator: generate-jwt
	docker-compose --env-file .env up validator &

stop-validator:
	docker stop validator-node morph-geth

rm-validator:
	docker rm validator-node morph-geth	


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

download-and-decompress-hoodi-snapshot:
	$(call download-and-decompress,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)

download-and-decompress-mainnet-snapshot:
	$(call download-and-decompress,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)

download-and-decompress-hoodi-mpt-snapshot:
	$(call download-and-decompress,$(HOODI_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)

download-and-decompress-mainnet-mpt-snapshot:
	$(call download-and-decompress,$(MAINNET_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)



