include .env

# Store the value of JWT_SECRET_FILE from .env
JWT_SECRET_FILE_MAINNET := $(JWT_SECRET_FILE)

include .env_holesky

include .env_hoodi

# Store the value of JWT_SECRET_FILE from .env_holesky
JWT_SECRET_FILE_HOLESKY := $(JWT_SECRET_FILE)

JWT_SECRET_FILE_HOODI := $(JWT_SECRET_FILE)

generate-jwt:
	@[ -f $(JWT_SECRET_FILE_MAINNET) ] || (echo "Generating $(JWT_SECRET_FILE_MAINNET)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_MAINNET) && echo "$(JWT_SECRET_FILE_MAINNET) created.")

generate-jwt-holesky:
	@[ -f $(JWT_SECRET_FILE_HOLESKY) ] || (echo "Generating $(JWT_SECRET_FILE_HOLESKY)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_HOLESKY) && echo "$(JWT_SECRET_FILE_HOLESKY) created.")

generate-jwt-hoodi:
	@[ -f $(JWT_SECRET_FILE_HOODI) ] || (echo "Generating $(JWT_SECRET_FILE_HOODI)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE_HOODI) && echo "$(JWT_SECRET_FILE_HOODI) created.")

## node management
run-node: generate-jwt
	docker-compose --env-file .env up node &

run-hoodi-node: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi up node &

run-holesky-node: generate-jwt-holesky
	docker-compose --env-file .env_holesky up node &

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
	docker-compose --env-file .env up validator &

run-hoodi-validator: generate-jwt-hoodi
	docker-compose --env-file .env_hoodi up validator &

run-holesky-validator: generate-jwt-holesky
	docker-compose --env-file .env_holesky up validator &

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
download-and-decompress-holesky-snapshot:
	$(call download-and-decompress,$(HOLESKY_SNAPSHOT_NAME),https://snapshot.morphl2.io/holesky)

download-and-decompress-hoodi-snapshot:
	$(call download-and-decompress,$(HOODI_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)

download-and-decompress-mainnet-snapshot:
	$(call download-and-decompress,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)

download-and-decompress-hoodi-mpt-snapshot:
	$(call download-and-decompress,$(HOODI_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/hoodi)

download-and-decompress-mainnet-mpt-snapshot:
	$(call download-and-decompress,$(MAINNET_MPT_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)



