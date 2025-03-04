#!/usr/bin/bash
set -e

if [ -z "$1" ]; then
    exit 1
fi

options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE"
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
        args="docker images --format {{.CreatedAt}}={{.Repository}}:{{.Tag}} | sort | cut -f 2 -d =";;
    get-env)
        args="cat ~/cabot_ws/cabot/.env";;
    software_update)
        ./remote-merge-env.sh $2
        scp $options -p ./host-setup.sh $CABOT_SSH_TARGET:/tmp/host-setup.sh
        args="/tmp/host-setup.sh";;
    site_update)
        ./remote-merge-env.sh $2
        scp $options -p ./host-setup.sh $CABOT_SSH_TARGET:/tmp/host-setup.sh
        args="/tmp/host-setup.sh";;
    env_update)
        ./remote-merge-env.sh $2
        scp $options -p ./host-setup.sh $CABOT_SSH_TARGET:/tmp/host-setup.sh
        args="/tmp/host-setup.sh";;
    *)
        args=$@;;
esac

echo $args 1>&2
ssh $options $CABOT_SSH_TARGET $args
