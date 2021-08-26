#!/bin/sh

# Check if config exists from existing installation (venv or previous docker launch)
if [ ! "$(ls -A ./app/config)" ]; then
    cp -r ./app/config_original/* ./app/config/
fi

exec python3 main.py $@
