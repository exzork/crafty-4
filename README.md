# Crafty Controller 4.0.0-alpha.3
> Python based Control Panel for your Minecraft Server

## What is Crafty Controller?
Crafty Controller is a Minecraft Server Control Panel / Launcher. The purpose
of Crafty Controller is to launch a Minecraft Server in the background and present
a web interface for the server administrators to interact with their servers. Crafty
is compatible with Docker, Linux, Windows 7, Windows 8 and Windows 10.

## Documentation
Temporary documentation available on [GitLab](https://gitlab.com/crafty-controller/crafty-commander/wikis/home)

## Meta
Project Homepage - https://craftycontrol.com

Discord Server - https://discord.gg/9VJPhCE

Git Repository - https://gitlab.com/crafty-controller/crafty-web

## Basic Docker Usage

**To get started with docker**, all you need to do is pull the image from this git repository's registry.
This is done by using `docker-compose` or `docker run`(You don't need to clone the Repository and build, like in 3.x ).

If you have a config folder already from previous local installation or docker setup, the image should mount this volume, if none is present then it will populate its own config folder for you.

### Using the registry image:
The provided image supports both `arm64` and `amd64` out the box, if you have issues though you can build it yourself.

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
Then use one of the following methods:
#### docker-compose.yml
```yml
version: '3'

services:
  crafty:
    container_name: crafty_commander
    image: registry.gitlab.com/crafty-controller/crafty-commander:latest
    ports:
      - "8000:8000" # HTTP
      - "8443:8443" # HTTPS
      - "8123:8123" # DYNMAP
      - "19132:19132/udp" # BEDROCK
      - "24000-25600:24000-25600" # MC SERV PORT RANGE
    volumes:
      - ./docker/backups:/commander/backups
      - ./docker/logs:/commander/logs
      - ./docker/servers:/commander/servers
      - ./docker/config:/commander/app/config
```

#### docker run
```sh
$ docker run \
	--name crafty_commander \
	-p 8000:8000 \
	-p 8443:8443 \
	-p 8123:8123 \
	-p 19132:19132/udp \
	-p 24000-25600:24000-25600 \
	-v "/$(pwd)/docker/backups:/commander/backups" \
	-v "/$(pwd)/docker/logs:/commander/logs" \
	-v "/$(pwd)/docker/servers:/commander/servers" \
	-v "/$(pwd)/docker/config:/commander/app/config" \
	registry.gitlab.com/crafty-controller/crafty-commander:latest
```

### Building from the cloned repository:

If you are building from `docker-compose` you can find the compose file in `./docker/docker-compose.yml` just `cd` to the docker directory and `docker-compose up -d`

If you'd rather not use `docker-compose` you can use the following `docker run`in the directory where the *Dockerfile* is:
```sh
# REMEMBER, Build your image first!
$ docker build . -t crafty

$ docker run \
	--name crafty_commander \
	-p 8000:8000 \
	-p 8443:8443 \
	-p 8123:8123 \
	-p 19132:19132/udp \
	-p 24000-25600:24000-25600 \
	-v "/$(pwd)/docker/backups:/commander/backups" \
	-v "/$(pwd)/docker/logs:/commander/logs" \
	-v "/$(pwd)/docker/servers:/commander/servers" \
	-v "/$(pwd)/docker/config:/commander/app/config" \
	crafty
```
A fresh build will take several minutes depending on your system, but will be rapid there after.
