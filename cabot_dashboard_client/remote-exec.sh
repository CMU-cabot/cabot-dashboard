#!/usr/bin/bash

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
        args="echo sudo systemctl reboot";;
    system-poweroff)
        args="echo sudo systemctl poweroff";;
    software_update)
        shift; args="echo software_update $@";;
    get-image-tags)
        args="docker images --format {{.Repository}}:{{.Tag}}";;
    *)
        args=$@;;
esac

echo $args 1>&2
options="-o StrictHostKeyChecking=no -i $CABOT_DASHBOARD_ID_FILE"
ssh $options $CABOT_DASHBOARD_USER_NAME@host_addr $args
