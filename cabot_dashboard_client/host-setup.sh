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

echo イメージとマップの取得
rm -rf $CABOT_SITE_PKG_DIR
mkdir -p $CABOT_SITE_PKG_DIR
(./manage-pkg.sh -r $CABOT_SITE_REPO -v $CABOT_SITE_VERSION -d -u)
# CABOT_SITE_PKG_DIRに依存。ないとpwdにダウンロード
echo Done

(./manage-pkg.sh -p $CABOT_LAUNCH_IMAGE_TAG)

echo セットアップとインストール
(./plugin-build.sh)
systemctl --user restart cabot-plugin
echo All Done
