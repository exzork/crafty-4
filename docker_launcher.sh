#!/bin/sh

# Check if config exists from existing installation (venv or previous docker launch)
if [ ! "$(ls -A ./app/config)" ]; then
    mkdir ./app/config/
    cp -r ./app/config_original/* ./app/config/
fi

# Set user/group permissions to env or default to image root
groupmod -g "${PGID}" -o crafty
sed -i -E "s/^(crafty:x):[0-9]+:[0-9]+:(.*)/\\1:$PUID:$PGID:\\2/" /etc/passwd

# Apply new permissions taken from env over working dirs
chown -R crafty:crafty \
    /commander/ \
    /commander-venv/

# Activate our prepared venv and launch crafty with provided args
. /commander-venv/bin/activate
exec python3 main.py $@
