# Crafty Controller 4.0.0-alpha.2
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

A Docker image pipeline is still to be implimented but for example you can expect the image to be located: `crafty/cc-dashboard` and you would change the image in the below `docker run` to this image.

If you are building from the `docker-compose` you can find it in `./docker/docker-compose.yml` just `cd` to the docker directory and `docker-compose up -d`

If you'd rather not use `docker-compose` you can use the following `docker run`:

```
$ docker build . -t cc-dashboard
# REMEMBER, Build your image!
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
	cc-dashboard
```
A fresh build will take several minutes depending on your system, but will be rapid there after.

If you have a config folder already from previous local installation or docker setup, the image should mount this volume, if none is present then it will populate its own config folder for you.
