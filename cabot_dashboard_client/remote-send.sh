#!/usr/bin/bash
set -e

if [ -z "$2" ]; then
    exit 1
fi

options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE -p"
scp $options $1 $CABOT_SSH_TARGET:$2
