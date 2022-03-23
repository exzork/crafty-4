[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Supported Python Versions](https://shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9-blue)](https://gitlab.com/crafty-controller/crafty-commander)
[![Version(temp-hardcoded)](https://img.shields.io/badge/release-v4.0.0--alpha3.5-orange)](https://gitlab.com/crafty-controller/crafty-commander)
[![Code Quality(temp-hardcoded)](https://img.shields.io/badge/code%20quality-10-brightgreen)](https://gitlab.com/crafty-controller/crafty-commander)
[![Build Status](https://gitlab.com/crafty-controller/crafty-commander/badges/master/pipeline.svg)](https://gitlab.com/crafty-controller/crafty-commander/-/commits/master)
# Crafty Controller 4.0.0-alpha.3.5
> Python based Control Panel for your Minecraft Server

## What is Crafty Controller?
Crafty Controller is a Minecraft Server Control Panel / Launcher. The purpose
of Crafty Controller is to launch a Minecraft Server in the background and present
a web interface for the server administrators to interact with their servers. Crafty
is compatible with Docker, Linux, Windows 7, Windows 8 and Windows 10.

## Documentation
Documentation available on [wiki.craftycontrol.com](https://craftycontrol.com)

## Meta
Project Homepage - https://craftycontrol.com

Discord Server - https://discord.gg/9VJPhCE

Git Repository - https://gitlab.com/crafty-controller/crafty-web

<br>

## Basic Docker Usage 🐳

With `Crafty Controller 4.0` we have focused on building our DevOps Principles, implementing build automation, and securing our containers, with the hopes of making our Container user's lives abit easier.

### - Two big changes you will notice is:
- We now provide pre-built images for you guys.
- Containers now run as non-root, using practices used by OpenShift & Kubernetes (root group perms).


> __**⚠ 🔻WARNING: [WSL/WSL2 | WINDOWS 11 | DOCKER DESKTOP]🔻**__ <br>
 BE ADVISED! Upstream is currently broken for Minecraft running on **Docker under WSL/WSL2, Windows 11 / DOCKER DESKTOP!** <br>
 On '**Stop**' or '**Restart**' of the MC Server, there is a 90% chance the World's Chunks will be shredded irreparably! <br>
 Please only run Docker on Linux, If you are using Windows we have a portable installs found here: [Latest-Stable](https://gitlab.com/crafty-controller/crafty-commander/-/jobs/artifacts/master/download?job=win-prod-build), [Latest-Development](https://gitlab.com/crafty-controller/crafty-commander/-/jobs/artifacts/dev/download?job=win-dev-build)

----

### - To get started with docker 🛫
All you need to do is pull the image from this git repository's registry.
This is done by using `'docker-compose'` or `'docker run'` (You don't need to clone the Repository and build, like in 3.x ).

If you have a config folder already from previous local installation or _docker setup_*, the image should mount this volume and fix the permission as required, if no config present then it will populate its own config folder for you. <br> <br>
As the Dockerfile uses the permission structure of `crafty:root` **internally** there is no need to worry about matching the `UID` or `GID` on the host system :)

<br>

### - Using the registry image 🌎
The provided image supports both `arm64` and `amd64` out the box, if you have issues though you can build it yourself with the `compose` file in `docker/`.

The image is located at: `registry.gitlab.com/crafty-controller/crafty-commander:latest`
| Branch             | Status                                                                |
| ----------------- | ------------------------------------------------------------------ |
| :latest | [![pipeline status](https://gitlab.com/crafty-controller/crafty-commander/badges/master/pipeline.svg)](https://gitlab.com/crafty-controller/crafty-commander/-/commits/master) |
| :dev | [![pipeline status](https://gitlab.com/crafty-controller/crafty-commander/badges/dev/pipeline.svg)](https://gitlab.com/crafty-controller/crafty-commander/-/commits/dev) |

While the repository is still **private / pre-release**,
Before you can pull the image you must authenticate docker with the Container Registry.

To authenticate you will need a [personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
with the minimum scope:

- For read (*pull*) access, `read_registry`.
- For write (*push*) access, `write_registry`.

When you have this just run:
```bash
$ docker login registry.gitlab.com -u <username> -p <token>
```
or
```bash
$ echo <token> | docker login registry.gitlab.com -u <username> --password-stdin
```
or
```bash
$ cat ~/my_password.txt | docker login registry.gitlab.com -u <username> --password-stdin
```

Then use one of the following methods:
### **docker-compose.yml:**
```sh
# Make your compose file
$ vim docker-compose.yml
```
```yml
version: '3'

services:
  crafty:
    container_name: crafty_commander
    image: registry.gitlab.com/crafty-controller/crafty-commander:latest
    environment:
      - TZ=Etc/UTC
    ports:
      - "8000:8000" # HTTP
      - "8443:8443" # HTTPS
      - "8123:8123" # DYNMAP
      - "19132:19132/udp" # BEDROCK
      - "25500-25600:25500-25600" # MC SERV PORT RANGE
    volumes:
      - ./docker/backups:/commander/backups
      - ./docker/logs:/commander/logs
      - ./docker/servers:/commander/servers
      - ./docker/config:/commander/app/config
      - ./docker/import:/commander/import
```
```sh
$ docker-compose up -d && docker-compose logs -f
```
<br>

### **docker run:**
```sh
$ docker run \
	--name crafty_commander \
	-p 8000:8000 \
	-p 8443:8443 \
	-p 8123:8123 \
	-p 19132:19132/udp \
	-p 25500-25600:25500-25600 \
	-e TZ=Etc/UTC \
	-v "/$(pwd)/docker/backups:/commander/backups" \
	-v "/$(pwd)/docker/logs:/commander/logs" \
	-v "/$(pwd)/docker/servers:/commander/servers" \
	-v "/$(pwd)/docker/config:/commander/app/config" \
	-v "/$(pwd)/docker/import:/commander/import" \
	registry.gitlab.com/crafty-controller/crafty-commander:latest
```

### **Building from the cloned repository:**

If you are building from `docker-compose` you can find the compose file in `./docker/docker-compose.yml` just `cd` to the docker directory and `docker-compose up -d`

If you'd rather not use `docker-compose` you can use the following `docker run` in the directory where the *Dockerfile* is:
```sh
# REMEMBER, Build your image first!
$ docker build . -t crafty

$ docker run \
	--name crafty_commander \
	-p 8000:8000 \
	-p 8443:8443 \
	-p 8123:8123 \
	-p 19132:19132/udp \
	-p 25500-25600:25500-25600 \
	-e TZ=Etc/UTC \
	-v "/$(pwd)/docker/backups:/commander/backups" \
	-v "/$(pwd)/docker/logs:/commander/logs" \
	-v "/$(pwd)/docker/servers:/commander/servers" \
	-v "/$(pwd)/docker/config:/commander/app/config" \
	-v "/$(pwd)/docker/import:/commander/import" \
	crafty
```
A fresh build will take several minutes depending on your system, but will be rapid thereafter.
