lint:
	# Check code syntax
	docker run -v ${CURDIR}:/apps alpine/flake8:latest .

deadcode:
	# Check for dead code
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest \
	--exclude docker/,submodules/ --min-confidence 90 .

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

run:
	# Run Django test server on http://127.0.0.1:8200
	python3 tests/manage.py runserver 0.0.0.0:8200

test:
	# Run all tests
	python3 tests/manage.py test testapp
