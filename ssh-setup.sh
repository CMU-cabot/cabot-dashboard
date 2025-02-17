#!/usr/bin/bash

# create key pair (no passphrase)
ssh-keygen -t rsa -f id_cabot -N ""
# add to authorized_keys
cat id_cabot.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys