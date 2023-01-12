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

build_docker_img:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build

rebuild_docker_img:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build --no-cache

lint:
ifndef IN_FLAKE8
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/flake8:latest make lint
else
	flake8 .
endif

deadcode:
ifndef IN_VULTURE
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest make deadcode
else
	vulture --exclude docker/,submodules/ --min-confidence 90 .
endif

run:
	# Run Django test server on http://127.0.0.1:8200
	${DOCKER_COMPOSE} up -e "NEED_CLAMAV=${NEED_CLAMAV}" --abort-on-container-exit

test:
ifndef DOCKER
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 -e "PYTEST_ARGS=${PYTEST_ARGS}" --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} make test
else
	pytest --reuse-db --cov=django_web_utils ${PYTEST_ARGS}
endif

shell:
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 -e "NEED_CLAMAV=${NEED_CLAMAV}" --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} /bin/bash

stop:
	${DOCKER_COMPOSE} stop && ${DOCKER_COMPOSE} rm -f

po:
	# Generate po files from source
ifndef DOCKER
	docker run --rm -it -e DOCKER_TEST=1 -v ${CURDIR}:/opt/src ${DOCKER_IMG} make po
else
	cd django_web_utils \
	&& django-admin makemessages --all --no-wrap
	cd django_web_utils/file_browser \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap
	cd django_web_utils/monitoring \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap
endif

mo:
	# Generate mo files from po files
ifndef DOCKER
	docker run --rm -it -e DOCKER_TEST=1 -v ${CURDIR}:/opt/src ${DOCKER_IMG} make mo
else
	cd django_web_utils \
	&& django-admin compilemessages
	cd django_web_utils/file_browser \
	&& django-admin compilemessages
	cd django_web_utils/monitoring \
	&& django-admin compilemessages
endif

clean:
	# Remove compiled Python files
	find . -name '*.pyc' -delete
	find . -name __pycache__ -type d -delete
