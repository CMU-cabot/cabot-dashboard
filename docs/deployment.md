# デプロイメント手順

## サーバーのデプロイ

### 前提条件
- Azure CLIがインストールされていること
- Azure Container Registry（ACR）へのアクセス権限があること

### デプロイ手順

1. Azure CLIでACRにログイン
```bash
az acr login --name <registry-name>
```

2. Dockerイメージのタグ付け
```bash
docker tag local-image-name:tag azure-image-name:tag
```

3. Azure Container Registryへのプッシュ
```bash
docker push azure-image-name:tag
```

4. Azure Web App for Containersへのデプロイ
- お試し環境：dev01-miraikan-dashboard-webapp
- ACRへのプッシュで自動デプロイ（要インスタンス設定）

### 環境変数設定

以下の環境変数を Azure Web App for Containers で設定する必要があります：

- `WEBSITES_PORT = 8000`
- `CABOT_DASHBOARD_LOG_LEVEL=INFO`
- `CABOT_DASHBOARD_LOG_TO_FILE=false`
- `CABOT_DASHBOARD_API_KEY=[api key]`
- `CABOT_DASHBOARD_SESSION_TIMEOUT=1800`
- `CABOT_DASHBOARD_MAX_ROBOTS=20`
- `CABOT_DASHBOARD_POLL_TIMEOUT=30`
- `CABOT_DASHBOARD_DEBUG_MODE=false`
- `CABOT_DASHBOARD_ALLOWED_CABOT_IDS`

## クライアントのデプロイ

### 環境変数設定

ロボット側で以下の環境変数を設定する必要があります：

- `CABOT_DASHBOARD_SERVER_URL=[URL]`
- `CABOT_DASHBOARD_API_KEY=[api key]`
- `CABOT_DASHBOARD_LOG_LEVEL=INFO`
- `CABOT_DASHBOARD_LOG_TO_FILE=false`
- `CABOT_DASHBOARD_POLLING_INTERVAL=1`
- `CABOT_DASHBOARD_CABOT_ID=cabot10`

### デプロイ手順

1. ロボット側でAzure Container Registryからイメージをプル
```bash
docker pull <registry-name>.azurecr.io/<image-name>:<tag>
```

2. コンテナの起動
```bash
docker run -d --env-file .env <image-name>
```

## ローカル開発環境

### Docker Compose

起動：
```bash
docker-compose up -d --build server
docker-compose up -d --build client
```

終了：
```bash
docker-compose down
```

### アクセス

- ローカル環境：http://localhost:8000
- クラウド環境：https://dev01-miraikan-dashboard-webapp.azurewebsites.net 