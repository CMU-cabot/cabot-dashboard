#!/usr/bin/bash

if [ -z "$2" ]; then
    exit 1
fi

options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE -p"
scp $options $CABOT_SSH_TARGET:$1 $2
