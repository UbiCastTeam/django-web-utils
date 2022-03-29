# expose .env variables globally
-include .env
export

DOCKER_IMG := django_web_utils
TMP_DOCKER_CT := django_web_utils_ct
DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml

build_docker_img:
	DOCKER_BUILDKIT=1 ${DOCKER_COMPOSE} build

lint:
ifndef CI
	docker run -e CI=1 --rm -v ${CURDIR}:/apps alpine/flake8:latest
else
	flake8 .
endif

deadcode:
ifndef CI
	docker run -e CI=1 --rm -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest \
		 --exclude docker/,submodules/ --min-confidence 90 .
else
	vulture --exclude docker/,submodules/ --min-confidence 90 .
endif

run:
	# Run Django test server on http://127.0.0.1:8200
	${DOCKER_COMPOSE} up --abort-on-container-exit
test:
ifndef CI
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} make test
else
	pytest --reuse-db --cov=django_web_utils ${PYTEST_ARGS}
endif

shell:
	${DOCKER_COMPOSE} run -e CI=1 -e DOCKER_TEST=1 --rm --name ${TMP_DOCKER_CT} ${DOCKER_IMG} /bin/bash

stop:
	${DOCKER_COMPOSE} stop && ${DOCKER_COMPOSE} rm -f

po:
	# Generate po files from source
	cd django_web_utils \
	&& django-admin makemessages --all --no-wrap
	cd django_web_utils/file_browser \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap
	cd django_web_utils/monitoring \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap

mo:
	# Generate mo files from po files
	cd django_web_utils \
	&& django-admin compilemessages
	cd django_web_utils/file_browser \
	&& django-admin compilemessages
	cd django_web_utils/monitoring \
	&& django-admin compilemessages

clean:
	# Remove compiled Python files
	find . -name '*.pyc' -delete
	find . -name __pycache__ -type d -delete
