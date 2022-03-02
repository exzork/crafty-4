FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive"

LABEL maintainer="Dockerfile created by Zedifus <https://gitlab.com/zedifus>"

# Security Patch for CVE-2021-44228
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

# Create non-root user & required dirs
RUN useradd -M crafty \
    && mkdir /commander \
    && chown -R crafty:root /commander

# Install required system packages
RUN apt-get update \
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
    && apt-get clean

# Switch to service user for installing crafty deps
USER crafty
WORKDIR /commander
COPY --chown=crafty:root requirements.txt ./
RUN python3 -m venv ./.venv \
    && . .venv/bin/activate \
    && pip3 install --no-cache-dir --upgrade setuptools==50.3.2 pip==22.0.3 \
    && pip3 install --no-cache-dir -r requirements.txt \
    && deactivate

# Copy Source w/ perms & prepare default config from example
COPY --chown=crafty:root ./ ./
RUN mv ./app/config ./app/config_original \
    && mv ./app/config_original/default.json.example ./app/config_original/default.json \
    && chmod +x ./docker_launcher.sh

# Expose Web Interface port & Server port range
EXPOSE 8000
EXPOSE 8443
EXPOSE 19132
EXPOSE 25500-25600

# Start Crafty Commander through wrapper
ENTRYPOINT ["/commander/docker_launcher.sh"]
CMD ["-v", "-d", "-i"]
