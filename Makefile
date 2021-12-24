lint:
	docker run -v ${CURDIR}:/apps alpine/flake8:latest .

deadcode:
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest \
	--exclude docker/,submodules/ --min-confidence 90 .

po:
	cd django_web_utils \
	&& django-admin makemessages --all --no-wrap
	cd django_web_utils/file_browser \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap
	cd django_web_utils/monitoring \
	&& django-admin makemessages --all --no-wrap \
	&& django-admin makemessages -d djangojs --all --no-wrap

mo:
	cd django_web_utils \
	&& django-admin compilemessages
	cd django_web_utils/file_browser \
	&& django-admin compilemessages
	cd django_web_utils/monitoring \
	&& django-admin compilemessages

clean:
	sudo find . -name '*.pyc' -delete
	sudo find . -name __pycache__ -type d -delete
