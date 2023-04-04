# expose .env variables globally
-include .env
export

# Pass local user uid and gid if greater than or equal 1000
USER_UID := $(shell id -u)
ifeq ($(shell expr $(USER_UID) \< 1000), 1)
	USER_UID := 1000
endif
USER_GID := $(shell id -g)
ifeq ($(shell expr $(USER_GID) \< 1000), 1)
	USER_GID := 1000
endif

DOCKER_IMG ?= django_web_utils
TMP_DOCKER_CT ?= django_web_utils_ct
DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml
NEED_CLAMAV ?= 0

docker_build:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build

docker_rebuild:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build --no-cache

lint:
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/flake8:latest make lint_local

lint_local:
	flake8 .

deadcode:
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest make deadcode_local

deadcode_local:
	vulture --exclude docker/,submodules/ --min-confidence 90 .

run:
	# Run Django test server on http://127.0.0.1:8200
	${DOCKER_COMPOSE} up --abort-on-container-exit

stop:
	${DOCKER_COMPOSE} stop && ${DOCKER_COMPOSE} rm -f

shell:
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 -e "NEED_CLAMAV=${NEED_CLAMAV}" --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} /bin/bash

test:
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 -e "PYTEST_ARGS=${PYTEST_ARGS}" --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} make test_local

test_local:
	pytest --reuse-db --cov=django_web_utils ${PYTEST_ARGS}

generate_po:
	# Generate po files from source
	docker run --rm -it -e DOCKER_TEST=1 -v ${CURDIR}:/opt/src ${DOCKER_IMG} make generate_po_local

generate_po_local:
	cd django_web_utils \
		&& django-admin makemessages --all --no-wrap
	cd django_web_utils/file_browser \
		&& django-admin makemessages --all --no-wrap \
		&& django-admin makemessages -d djangojs --all --no-wrap
	cd django_web_utils/monitoring \
		&& django-admin makemessages --all --no-wrap \
		&& django-admin makemessages -d djangojs --all --no-wrap

generate_mo:
	# Generate mo files from po files
	docker run --rm -it -e DOCKER_TEST=1 -v ${CURDIR}:/opt/src ${DOCKER_IMG} make generate_mo_local

generate_mo_local:
	cd django_web_utils \
		&& django-admin compilemessages
	cd django_web_utils/file_browser \
		&& django-admin compilemessages
	cd django_web_utils/monitoring \
		&& django-admin compilemessages

translate:
	make generate_po
	docker run -v ${CURDIR}:/apps registry.ubicast.net/devtools/translator:main translator \
		--api-key "${DEEPL_API_KEY}" \
		--path django_web_utils \
		--source-language EN \
		--target-language DE \
		--target-language ES \
		--target-language FI \
		--target-language FR \
		--target-language NL \
		--glossaries-dir deepl_glossaries \
		--mark-language-fuzzy FR \
		--log-level=info ${TRANSLATE_ARGS}
	make generate_po
	make generate_mo

clean:
	# Remove compiled Python files
	find . -name '*.pyc' -delete
	find . -name __pycache__ -type d -delete
