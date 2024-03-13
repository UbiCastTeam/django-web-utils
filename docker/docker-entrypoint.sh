#!/usr/bin/env bash

if [[ "$NEED_CLAMAV" == "1" ]]; then
    echo "==> Starting ClamAV..."
    # The systemctl command is not available here
    sudo service clamav-daemon start
fi

if [[ ! "$DOCKER_TEST" ]]; then
    echo "==> Waiting until the database is up and ready..."
    while !</dev/tcp/db/5432; do sleep 1; done;

    echo "==> Applying migrations..."
    python3 tests/manage.py migrate

    echo "==> Creating superuser..."
    DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=test@example.com DJANGO_SUPERUSER_PASSWORD=test python3 tests/manage.py createsuperuser --noinput

    echo "==> Creating magic login file..."
    mkdir /tmp/djwutils
    echo '{"magic@example.com": {"username": "magic-user", "first_name": "Magic", "last_name": "User", "is_staff": true, "is_superuser": true}}' > /tmp/djwutils/users.json
fi

echo "==> Running $@"
exec "$@"
