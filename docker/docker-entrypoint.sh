#!/usr/bin/env bash

echo "==> Starting ClamAV..."
# The systemctl command is not available here
service clamav-daemon start

if [[ ! "$DOCKER_TEST" ]]; then
    echo "==> Waiting until the database is up and ready..."
    while !</dev/tcp/db/5432; do sleep 1; done;

    echo "==> Applying migrations..."
    python3 tests/manage.py migrate
fi

echo "==> Running $@"
exec "$@"
