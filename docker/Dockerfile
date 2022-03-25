FROM debian

ARG CLAMAV_MIRROR="database.clamav.net"

# System
RUN apt-get -q update && apt-get -qy install --no-install-recommends \
        ca-certificates curl gnupg sudo moreutils wget unzip make bash \
        git git-lfs postgresql-client python3 python3-setuptools \
        python3-pip clamav-daemon

RUN pip install --upgrade pip
RUN pip install pytest pytest-cov pytest-django
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Update clamav database
RUN chmod 644 /etc/clamav/freshclam.conf
RUN sed -i 's/DatabaseMirror/#DatabaseMirror/gi' /etc/clamav/freshclam.conf
RUN echo "DatabaseMirror $CLAMAV_MIRROR" >> /etc/clamav/freshclam.conf
RUN freshclam

WORKDIR /opt/src

EXPOSE 8200

ENTRYPOINT ["./docker/docker-entrypoint.sh"]
