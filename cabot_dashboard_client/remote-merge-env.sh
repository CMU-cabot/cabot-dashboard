#!/usr/bin/bash
set -e

if [ -z "$1" ]; then
    exit 1
fi

remote_env="~/cabot_ws/cabot/.env"
original_env="/tmp/original.env"
update_env=$1
result_env="/tmp/result.env"
options="-o StrictHostKeyChecking=no -i $CABOT_SSH_ID_FILE -p"
if [ ! -f "$update_env" ]; then
  echo "Error: $update_env does not exist."
  exit 1
fi

scp $options $CABOT_SSH_TARGET:$remote_env $original_env
python merge-env.py $original_env $update_env $result_env
scp $options $result_env $CABOT_SSH_TARGET:$remote_env
