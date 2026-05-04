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

DOCKER_IMAGE ?= django_web_utils
DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml
DOCKER_RUN := docker run --rm -it --name django_web_utils_ct -v ${CURDIR}:/opt/src -w /opt/src
NEED_CLAMAV ?= 0

docker_build:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build

docker_rebuild:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build --no-cache

lint:
	${DOCKER_RUN} --entrypoint /usr/bin/make ${DOCKER_IMAGE} lint_local

lint_local:
	ruff check

deadcode:
	${DOCKER_RUN} --entrypoint /usr/bin/make ${DOCKER_IMAGE} deadcode_local

deadcode_local:
	vulture --exclude docker/,submodules/ --min-confidence 90 .

run:
	# Run Django test server on http://127.0.0.1:8200
	${DOCKER_COMPOSE} up

stop:
	${DOCKER_COMPOSE} down

shell:
	${DOCKER_COMPOSE} run -e DOCKER_TEST=1 -e "NEED_CLAMAV=${NEED_CLAMAV}" --rm ${DOCKER_IMAGE} /bin/bash

test:
	${DOCKER_COMPOSE} run -e DOCKER_TEST=1 -e "PYTEST_ARGS=${PYTEST_ARGS}" --rm ${DOCKER_IMAGE} make test_local

test_local:PYTEST_ARGS := $(or ${PYTEST_ARGS},--cov --cov-report html --cov-report term tests/testapp/tests)
test_local:
	pytest --reuse-db ${PYTEST_ARGS}

test_install:
	${DOCKER_RUN} --user root --entrypoint /usr/bin/make ${DOCKER_IMAGE} test_install_local

test_install_local:
	# List files that will be installed
	make clean
	rm /opt/venv/lib/python3.11/site-packages/django_web_utils
	cp -a /opt/src /tmp/src
	cd /tmp/src && /opt/venv/bin/pip install .
	cd /tmp/src && /opt/venv/bin/pip show -f django-web-utils

generate_po:
	# Generate po files from source
	${DOCKER_RUN} -e DOCKER_TEST=1 ${DOCKER_IMAGE} make generate_po_local

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
	${DOCKER_RUN} -e DOCKER_TEST=1 ${DOCKER_IMAGE} make generate_mo_local

generate_mo_local:
	cd django_web_utils \
		&& django-admin compilemessages
	cd django_web_utils/file_browser \
		&& django-admin compilemessages
	cd django_web_utils/monitoring \
		&& django-admin compilemessages

translate:
	make generate_po
	${DOCKER_RUN} --user "${USER_UID}:${USER_GID}" registry.ubicast.net/devtools/translator:main translator \
		--api-key "${DEEPL_API_KEY}" \
		--path django_web_utils \
		--source-language EN \
		--target-language DE \
		--target-language ES \
		--target-language FI \
		--target-language FR \
		--target-language IT \
		--target-language NL \
		--glossaries-dir deepl_glossaries \
		--mark-language-fuzzy FR \
		--log-level=info ${TRANSLATE_ARGS}
	make generate_po
	make generate_mo

clean:
	# Remove compiled Python files
	rm -rf build django_web_utils.egg-info
	find . -name '*.pyc' -delete
	find . -name __pycache__ -type d -delete
