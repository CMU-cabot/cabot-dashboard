# cabot dashboard

複数のロボットを管理する仕組み

- ロボットのメトリクス状態の表示は Grafana で行う（cabot-grafana）
- ロボットの遠隔操作は、Grafanaとは別に用意するこちらの管理画面で行う

## 構成

- ロボット（dashboard-client）
  - ロボットの状態を取得する
  - ロボットの操作を行う
- ダッシュボード (dashboard-web)
  - ロボットの状態を表示する
  - ロボットの操作を行う
- APIサーバー (dashboard-server)
  - ロボットの状態を取得する
  - ロボットの操作を行う
  - ロボットの状態を表示する
  - ロボットの操作を行う

## アーキテクチャ

- 概要図
```mermaid
graph TB
    subgraph "開発環境"
        Dev[開発者]
        LocalDocker[ローカルDocker]
    end

    subgraph "Azure"
        ACR[Azure Container Registry]
        WebApp[Azure Web App for Container]
        Blob[Azure Blob Storage]
        Webhook[Webhook]
    end

    subgraph "ロボット"
        ROS[ROS]
        ClientDocker[Clientコンテナ]
    end

    subgraph "運営"
        PC[PC]
        Smartphone[スマートフォン]
    end

    Dev -->|Dockerイメージをpush| LocalDocker
    LocalDocker -->|イメージをpush| ACR
    ACR -->|イメージ変更を通知| Webhook
    Webhook -->|自動デプロイ| WebApp
    ACR -->|イメージをpull| WebApp
    ACR -->|イメージをpull| ClientDocker
    Dev -->|Webファイルを手動アップロード| Blob
    ROS -->|起動| ClientDocker
    PC -->|アクセス| Blob
    Smartphone -->|アクセス| Blob
    PC -->|WebSocket接続| WebApp
    Smartphone -->|WebSocket接続| WebApp
    ClientDocker -->|WebSocket接続| WebApp

    classDef azure fill:#0072C6,stroke:#fff,stroke-width:2px,color:#fff;
    class ACR,WebApp,Blob,Webhook azure;
```

- 構成要素はDockerで管理
  - Serverはクラウド上に構築しDockerコンテナで起動
  - ClientはAIスーツ側に配置しDockerコンテナで起動（ROS or Ubuntu）
  - Webは静的Webサイトとして配置

- WebSocket で通信
  - ロボットとダッシュボードの間でメッセージをやり取りする

- Pythonで実装
  - サーバサイドは、FastAPIのフレームワークを利用

-  Server接続の認証方式（要検討）


## プロトタイプ

1. `main.py` を実行してサーバーを起動します。
2. `robot.py` を実行してロボットをシミュレートします。
3. `dashboard.py` を実行してダッシュボードをシミュレートします。

### シーケンス図

``` mermaid
sequenceDiagram
    participant User as ユーザー
    participant Docker as Dockerコンテナ
    participant Server as main.py (Server)
    participant Robot as robot.py (Robot)
    participant Dashboard as dashboard.html (Dashboard)

    User->>Docker: コンテナ起動
    Docker->>Server: main.py実行
    Server->>Server: FastAPIサーバー起動

    Robot->>Server: WebSocket接続要求
    Server->>Robot: 接続確立
    Dashboard->>Server: WebSocket接続要求
    Server->>Dashboard: 接続確立

    loop ロボットの状態更新
        Robot->>Robot: ステータス生成
        Robot->>Server: ステータス送信
        Server->>Server: メッセージ受信
        Server->>Dashboard: ステータス転送
        Dashboard->>Dashboard: メッセージ表示
    end

    alt タイムアウト発生
        Server->>Server: タイムアウト検出
        Server->>Dashboard: タイムアウト通知
    else 接続切断
        Robot->>Server: 切断
        Server->>Dashboard: 切断通知
    end

    loop 再接続
        Robot->>Server: 再接続試行
        Server->>Robot: 接続再確立
    end

    User->>Docker: コンテナ停止
    Docker->>Server: 終了シグナル
    Server->>Server: クリーンアップ
    Server->>Robot: 接続終了
    Server->>Dashboard: 接続終了
```

## Docker

起動
```
docker-compose up -d --build
```

終了
```
docker-compose down
```

## デプロイ手順

### Server

1. azコマンドで ACR へ loginしておく

2. Dockerイメージタグをつける
  ```
  docker tag cabot-dashboard-server:latest pqdev01miraikan.azurecr.io/cabot-dashboard-server:0.1
  ```
3. Azure Container Resistoryにpush
  ```
  docker push pqdev01miraikan.azurecr.io/cabot-dashboard-server:0.1
  ```
4. Azure Web App for Containersにデプロイ

- お試し環境
  - dev01-miraikan-dashboard-webapp
  - ACRへPushすると自動でデプロイ（インスタンス削除してる場合は再設定必要）

- 環境変数
  - WEBSITES_PORT = 8000
  - ~~ WEBSITES_WEBSOCKETS_ENABLED = 1 ~~
  - https://learn.microsoft.com/ja-jp/azure/app-service/reference-app-settings?source=recommendations&tabs=kudu%2Cdotnet

### Client

- ロボット側で Azure Container Registry から pull

### Web

- Blobストレージの静的サイトに配置
  - （サーバのコンテナにまとめられたらまとめる）


## 参考）開発環境（Python仮想環境の構築）

※dockerで動かす場合はここは不要
Pythonの仮想環境を構築するコマンド。Pythonがすでにインストールされているという前提。

1. 仮想環境を作成する：

```
python -m venv env
```

ここで、`env`は仮想環境の名前です。好きな名前に変更できます。

1. 仮想環境を有効化する：

Windowsの場合：
```
myenv\Scripts\activate
```

macOSやLinuxの場合：
```
source myenv/bin/activate
```

3. 仮想環境が有効化されたら、必要なパッケージをインストールできます：

```
pip install fastapi uvicorn websockets
```

4. 仮想環境を終了する場合：

```
deactivate
```

## TODO
- [ ] メッセージ仕様
- [ ] API認証
- [ ] 管理画面認証
- [ ] 管理画面UI設計
- [ ] 管理項目の確定
- [ ] クライアント側アクション実行
- [ ] サーバ側のデータ管理
- [ ] 性能測定
