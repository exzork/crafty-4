FROM python:alpine

LABEL maintainer="Dockerfile created by Zedifus <https://gitlab.com/zedifus>"

# Security Patch for CVE-2021-44228
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

# Install Packages & Garbage Collect Compile Deps & Harden
COPY requirements.txt /commander/requirements.txt
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/latest-stable/community \
gcc musl-dev libffi-dev make rust cargo openssl-dev llvm11-libs \
openjdk8-jre-base openjdk11-jre-headless openjdk16-jre-headless openjdk17-jre-headless mariadb-dev \
&& pip3 install --no-cache-dir -r /commander/requirements.txt \
&& apk del --no-cache gcc musl-dev libffi-dev make rust cargo openssl-dev llvm11-libs \
&& rm -rf /sbin/apk \
&& rm -rf /etc/apk \
&& rm -rf /lib/apk \
&& rm -rf /usr/share/apk \
&& rm -rf /var/lib/apk

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
