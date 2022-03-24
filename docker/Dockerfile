FROM debian

# System
RUN apt-get -q update && apt-get -qy install --no-install-recommends ca-certificates curl gnupg sudo moreutils wget unzip make bash

RUN curl -sL https://skyreach.ubicast.net/media/public.gpg | apt-key add -
RUN echo "deb https://skyreach.ubicast.net packaging/apt/$SKYREACH_APT_TOKEN/" > /etc/apt/sources.list.d/skyreach.list

RUN apt-get -q update && \
    apt-get -qy install --no-install-recommends \
        git \
        git-lfs \
        postgresql-client \
        python3 \
        python3-setuptools \
        python3-pip

RUN pip install pytest pytest-cov pytest-django

COPY requirements-debian.txt /tmp/requirements-debian.txt
RUN apt-get -qy install --no-install-recommends $(grep -v '^#' /tmp/requirements-debian.txt | cut -d ' ' -f1 | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/ /g')

# Update clamav database
RUN chmod 644 /etc/clamav/freshclam.conf
RUN sed -i 's/DatabaseMirror/#DatabaseMirror/gi' /etc/clamav/freshclam.conf
RUN echo "DatabaseMirror $CLAMAV_MIRROR" >> /etc/clamav/freshclam.conf
RUN freshclam

WORKDIR /opt/src

EXPOSE 8200

ENTRYPOINT ["./docker/docker-entrypoint.sh"]

CMD ["/bin/bash"]
