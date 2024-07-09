FROM debian:bookworm

ENV LANG="C.UTF-8"
ENV LC_ALL="C.UTF-8"

# Update clamav database
RUN apt-get -q update && apt-get -qy install --no-install-recommends \
        ca-certificates clamav-daemon
ARG CLAMAV_MIRROR
RUN echo "PrivateMirror $CLAMAV_MIRROR" >> /etc/clamav/freshclam.conf
RUN sed -i -E 's/^PrivateMirror\s+$//g' /etc/clamav/freshclam.conf
RUN freshclam

# Basic packages
RUN apt-get -q update && apt-get -qy install --no-install-recommends \
        curl gnupg sudo moreutils unzip make bash git git-lfs gettext \
        postgresql-client python3 python3-setuptools python3-venv

# Python venv
RUN python3 -m venv /opt/venv --system-site-packages
ENV PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
RUN pip install --upgrade pip setuptools wheel
COPY setup.py setup.py
RUN pip install --no-cache-dir -e '.[dev]'
RUN rm setup.py
RUN ln -sf /opt/src/django_web_utils /opt/venv/lib/python3.11/site-packages/django_web_utils

RUN mkdir -p /opt/src
WORKDIR /opt/src

# Add user matching local uid/gid
ARG USER_UID
ARG USER_GID
RUN groupadd --gid $USER_GID devuser
RUN useradd --uid $USER_UID --gid $USER_GID --home-dir /home/devuser --groups sudo --shell /bin/bash devuser
RUN echo "devuser ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER devuser

EXPOSE 8200

ENTRYPOINT ["./docker/docker-entrypoint.sh"]
