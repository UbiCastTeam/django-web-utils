FROM debian:bullseye

# Update clamav database
RUN apt-get -q update && apt-get -qy install --no-install-recommends \
        ca-certificates clamav-daemon
ARG CLAMAV_MIRROR
RUN echo "PrivateMirror $CLAMAV_MIRROR" >> /etc/clamav/freshclam.conf
RUN sed -i -E 's/^PrivateMirror\s+$//g' /etc/clamav/freshclam.conf
RUN freshclam

# Basic packages
RUN apt-get -q update && apt-get -qy install --no-install-recommends \
        curl gnupg sudo moreutils unzip make bash git git-lfs \
        postgresql-client python3 python3-setuptools python3-pip

RUN mkdir -p /opt/src
WORKDIR /opt/src

# PIP dependencies
RUN pip3 install --upgrade pip
COPY setup.py setup.py
RUN pip3 install --no-cache-dir -e '.[dev]'
RUN rm setup.py

EXPOSE 8200

ENTRYPOINT ["./docker/docker-entrypoint.sh"]
