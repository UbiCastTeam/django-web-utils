#!/usr/bin/env sh

echo -e "\e[44mStarting ClamAV...\e[0m"
# The systemctl command is not available here
service clamav-daemon start

exec "$@"