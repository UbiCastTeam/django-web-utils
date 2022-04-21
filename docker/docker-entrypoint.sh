#!/usr/bin/env bash

echo "==> Starting ClamAV..."
# The systemctl command is not available here
service clamav-daemon start

if [[ ! "$DOCKER_TEST" ]]; then
    echo "==> Waiting until the database is up and ready..."
    while !</dev/tcp/db/5432; do sleep 1; done;

    echo "==> Applying migrations..."
    python3 tests/manage.py migrate

    echo "==> Creating superuser..."
    DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=test@example.com DJANGO_SUPERUSER_PASSWORD=test python3 tests/manage.py createsuperuser --noinput
fi

echo "==> Running $@"
exec "$@"
