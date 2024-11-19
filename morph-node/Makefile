include .env

generate-jwt:
	@[ -f $(JWT_SECRET_FILE) ] || (echo "Generating $(JWT_SECRET_FILE)..." && openssl rand -hex 32 > $(JWT_SECRET_FILE) && echo "$(JWT_SECRET_FILE) created.")

## node management
run-node: generate-jwt
	docker-compose up node &

stop-node:
	docker stop morph-node morph-geth

rm-node:
	docker rm morph-node morph-geth

## validator management
run-validator: generate-jwt
	docker-compose up validator &

stop-validator:
	docker stop validator-node morph-geth

rm-validator:
	docker rm validator-node morph-geth	


download-and-decompress-holesky-snapshot:
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
	echo "Downloading ${HOLESKY_SNAPSHOT_NAME}.tar.gz from https://snapshot.morphl2.io/holesky..."; \
	if wget -q --show-progress -O ${HOLESKY_SNAPSHOT_NAME}.tar.gz https://snapshot.morphl2.io/holesky/${HOLESKY_SNAPSHOT_NAME}.tar.gz; then \
		echo "${HOLESKY_SNAPSHOT_NAME}.tar.gz downloaded successfully."; \
	else \
		echo "Error downloading ${HOLESKY_SNAPSHOT_NAME}.tar.gz."; \
		exit 1; \
	fi; \
	echo "Decompressing ${HOLESKY_SNAPSHOT_NAME}.tar.gz..."; \
	if tar -xzvf ${HOLESKY_SNAPSHOT_NAME}.tar.gz; then \
		echo "${HOLESKY_SNAPSHOT_NAME}.tar.gz decompressed successfully."; \
	else \
		echo "Error decompressing ${HOLESKY_SNAPSHOT_NAME}.tar.gz."; \
		exit 1; \
	fi; \
	rm -rf ${HOLESKY_SNAPSHOT_NAME}.tar.gz; 



