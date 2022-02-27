FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive"

LABEL maintainer="Dockerfile created by Zedifus <https://gitlab.com/zedifus>"

# Security Patch for CVE-2021-44228
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

# Install Packages, Dependencies and Setup user
COPY requirements.txt /commander-venv/requirements.txt
RUN groupadd -g "${PGID:-0}" -o crafty \
    && useradd -g "${PGID:-0}" -u "${PUID:-0}" -o crafty \
    && apt-get update \
    && apt-get -y --no-install-recommends install \
        gcc \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        libmariadb-dev \
        default-jre \
        openjdk-8-jre-headless \
        openjdk-11-jre-headless \
        openjdk-16-jre-headless \
        openjdk-17-jre-headless \
    && apt-get autoremove \
    && apt-get clean \
    && python3 -m venv /commander-venv/ \
    && . /commander-venv/bin/activate \
    && pip3 install --no-cache-dir --upgrade setuptools==50.3.2 pip==20.3.3 \
    && pip3 install --no-cache-dir -r /commander-venv/requirements.txt \
    && deactivate \
    && chown -R crafty:crafty /commander-venv

# Copy Source & copy default config from image
COPY ./ /commander
WORKDIR /commander
RUN mv ./app/config ./app/config_original \
    && mv ./app/config_original/default.json.example ./app/config_original/default.json \
    && chown -R crafty:crafty /commander \
    && chmod +x ./docker_launcher.sh

# Expose Web Interface port & Server port range
EXPOSE 8000
EXPOSE 8443
EXPOSE 19132
EXPOSE 25500-25600

# Start Crafty Commander through wrapper as crafty
USER crafty
ENTRYPOINT ["/commander/docker_launcher.sh"]
CMD ["-v", "-d", "-i"]
