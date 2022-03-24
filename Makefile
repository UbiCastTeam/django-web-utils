# expose .env variables globally
-include .env
export

DOCKER_IMG := django_web_utils
TMP_DOCKER_CT := django_web_utils_ct

build_docker_img:
	DOCKER_BUILDKIT=1 docker build --build-arg SKYREACH_APT_TOKEN=${SKYREACH_APT_TOKEN} --build-arg CLAMAV_MIRROR=${CLAMAV_MIRROR} -t ${DOCKER_IMG} -f docker/Dockerfile .

lint:
ifndef CI
	docker run -e CI=1 -v ${CURDIR}:/apps alpine/flake8:latest
else
	flake8 .
endif

deadcode:
ifndef CI
	docker run -e CI=1 -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest
else
	vulture --exclude docker/,submodules/ --min-confidence 90 .
endif

run:
	# Run Django test server on http://127.0.0.1:8200
	docker run --rm -v ${CURDIR}:/opt/src -p 8200:8200 --name ${TMP_DOCKER_CT} ${DOCKER_IMG} python3 tests/manage.py runserver 0.0.0.0:8200

test:
ifndef CI
	docker run -e CI=1 --rm -v ${CURDIR}:/opt/src --name ${TMP_DOCKER_CT} ${DOCKER_IMG} make test
else
	pytest --reuse-db --cov=django_web_utils ${PYTEST_ARGS}
endif

shell:
	docker run -it --rm -v ${CURDIR}:/opt/src --name ${TMP_DOCKER_CT} ${DOCKER_IMG} /bin/bash

stop:
	docker kill ${TMP_DOCKER_CT} || true
	docker rm ${TMP_DOCKER_CT} || true

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
