#!/usr/bin/bash

if [ -z "$2" ]; then
    exit 1
fi

options="-o StrictHostKeyChecking=no -i $CABOT_DASHBOARD_ID_FILE -p"
scp $options $1 $CABOT_DASHBOARD_USER_NAME@host_addr:$2
