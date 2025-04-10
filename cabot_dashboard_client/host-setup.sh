#!/usr/bin/bash

# cd ~/cabot_ws/cabot/
: ${CABOT_WORKDIR:=~/cabot_ws/cabot}
: ${CABOT_SITE_PKG_DIR:=${CABOT_WORKDIR}/cabot-navigation/cabot_site_pkg}
: ${CABOT_LAUNCH_IMAGE_TAG:=latest}
cd $CABOT_WORKDIR

. .env
echo workdir:$CABOT_WORKDIR 
echo image-tag:$CABOT_LAUNCH_IMAGE_TAG
echo pkg-dir:$CABOT_SITE_PKG_DIR 
echo site-repo:$CABOT_SITE_REPO 
echo site-version:$CABOT_SITE_VERSION

systemctl --user stop cabot

echo Setup dependency
git fetch -p
git checkout $CABOT_LAUNCH_IMAGE_TAG
(./setup-dependency.sh)
echo Done

echo Getting docker images and map data
mkdir -p $CABOT_SITE_PKG_DIR
rm -rf $CABOT_SITE_PKG_DIR/$CABOT_SITE_REPO  # delete pkg only, do not delete downloaded zip
(./manage-pkg.sh -r $CABOT_SITE_REPO -v $CABOT_SITE_VERSION -d -u)
# depends on CABOT_SITE_PKG_DIR, download to the current working dir if not exisit
echo Done

(./manage-pkg.sh -p $CABOT_LAUNCH_IMAGE_TAG)

echo Set up and Install
(./build-workspace.sh -o)  # build host ros workspace
(./plugin-build.sh -s)
echo All Done
