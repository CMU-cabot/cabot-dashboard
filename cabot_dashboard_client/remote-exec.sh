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
    get-env)
        args="cat ~/cabot_ws/cabot/.env";;
    software_update)
        ./remote-merge-env.sh $2
        args="echo success";;
    site_update)
        ./remote-merge-env.sh $2
        args="echo success";;
    env_update)
        ./remote-merge-env.sh $2
        args="echo success";;
    *)
        args=$@;;
esac

echo $args 1>&2
options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE"
ssh $options $CABOT_SSH_TARGET $args
