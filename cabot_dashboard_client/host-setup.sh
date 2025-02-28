#!/usr/bin/bash
cd ~/cabot_ws/cabot/

. .env
echo pkg-dir:$CABOT_SITE_PKG_DIR site-repo:$CABOT_SITE_REPO site-version:$CABOT_SITE_VERSION

systemctl --user stop cabot

echo Setup dependency
(./setup-dependency.sh)
echo Done

echo イメージとマップの取得
mkdir -p $CABOT_SITE_PKG_DIR
(./manage-pkg.sh -r $CABOT_SITE_REPO -v $CABOT_SITE_VERSION -d -u)
#CABOT_SITE_PKG_DIRに依存。ないとpwdにダウンロード
echo Done

docker compose --profile build pull
#CABOT_LAUNCH_IMAGE_TAGに依存。ないとlatestを取得

echo セットアップとインストール
(./plugin-build.sh)
docker compose -f docker-compose-plugins.yaml pull
echo All Done
