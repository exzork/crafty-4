#!/bin/sh

# Check if config exists from existing installation (venv or previous docker launch)
if [ ! "$(ls -A --ignore=.gitkeep ./app/config)" ]; then
    echo "Wrapper | Config not found, pulling defaults..."
    mkdir ./app/config/ 2> /dev/null
    cp -r ./app/config_original/* ./app/config/
fi


if [ $(id -u) -eq 0 ]; then
    # We're running as root;
    # Need to ensure all dirs are owned by the root group,
    # This fixes bind mounts that may have incorrect perms.

    # Look for files & dirs that require group permissions to be fixed
    echo "Wrapper | Looking for problem bind mount permissions"
    find . ! -group root -exec chgrp root {} \;
    find . ! -perm g+rw -exec chmod g+rw {} \;
    find . -type d ! -perm g+s -exec chmod g+s {} \;

    # Switch user, activate our prepared venv and lauch crafty
    args="$@"
    echo "Wrapper | Launching crafty with [$args]"
    exec sudo -u crafty bash -c "source ./.venv/bin/activate && exec python3 main.py $args"
else
    # Activate our prepared venv
    echo "Wrapper | Non-root host detected, using normal exec"
    . ./.venv/bin/activate
    # Use exec as our perms are already correct
    # This is likely if using Kubernetes/OpenShift etc
    exec python3 main.py $@
fi
