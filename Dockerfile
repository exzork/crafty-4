FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive"

LABEL maintainer="Dockerfile created by Zedifus <https://gitlab.com/zedifus>"

# Security Patch for CVE-2021-44228
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

# Install Packages And Dependencies
COPY requirements.txt /commander/requirements.txt
RUN apt update \
&& apt install -y gcc python3 python3-pip libmariadb-dev openjdk-8-jre-headless openjdk-11-jre-headless openjdk-16-jre-headless openjdk-17-jre-headless default-jre \
&& pip3 install --no-cache-dir -r /commander/requirements.txt

# Copy Source & copy default config from image
COPY ./ /commander
WORKDIR /commander
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
