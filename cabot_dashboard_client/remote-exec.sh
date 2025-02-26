#!/usr/bin/bash
set -e

if [ -z "$1" ]; then
    exit 1
fi

case $1 in
    cabot-is-active)
        args="systemctl --user is-active cabot";;
    ros-start)
        args="systemctl --user start cabot";;
    ros-stop)
        args="systemctl --user stop cabot";;
    system-reboot)
        args="sudo systemctl reboot";;
    system-poweroff)
        args="sudo systemctl poweroff";;
    get-image-tags)
        args="docker images --format {{.Repository}}:{{.Tag}}";;
    software_update)
        echo CABOT_LAUNCH_IMAGE_TAG=$2 > /tmp/update.env
        ./remote-merge-env.sh /tmp/update.env
        exit 0;;
    *)
        args=$@;;
esac

echo $args 1>&2
options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE"
ssh $options $CABOT_SSH_TARGET $args
