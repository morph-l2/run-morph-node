include .env

generate-jwt:
	@[ -f $(JWT_SECRET_FILE) ] || (echo "Generating $(JWT_SECRET_FILE)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE) && echo "$(JWT_SECRET_FILE) created.")

## node management
run-node: generate-jwt
	docker-compose up node &

run-holesky-node: generate-jwt
	docker-compose --env-file .env_holesky up node &

stop-node:
	docker stop morph-node morph-geth

rm-node:
	docker rm morph-node morph-geth

## validator management
run-validator: generate-jwt
	docker-compose up validator &

run-holesky-validator: generate-jwt
	docker-compose --env-file .env_holesky up validator &

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

download-and-decompress-mainnet-snapshot:
	$(call download-and-decompress,$(MAINNET_SNAPSHOT_NAME),https://snapshot.morphl2.io/mainnet)




