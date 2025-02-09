#!/usr/bin/bash

if [ -z "$1" ]; then
    exit 1
fi

options="-o StrictHostKeyChecking=no -i $CABOT_DASHBOARD_ID_FILE"
ssh $options $CABOT_DASHBOARD_USER_NAME@host_addr $@
