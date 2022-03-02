#!/bin/sh

# Check if config exists from existing installation (venv or previous docker launch)
if [ ! "$(ls -A --ignore=.gitkeep ./app/config)" ]; then
    mkdir ./app/config/
    cp -r ./app/config_original/* ./app/config/
fi

# Activate our prepared venv and launch crafty with provided args
. .venv/bin/activate
exec python3 main.py $@
