# システムアーキテクチャ

## システム概要

Cabot Dashboardは、複数のロボットを管理するためのシステムです。主な機能は以下の通りです：

- ロボットのメトリクス状態の表示（Grafana連携）
- ロボットの遠隔操作

## システム構成

### コンポーネント

1. ロボット側（dashboard-client）
   - ロボットの状態取得
   - ロボットの操作実行
   - Dockerコンテナとして実行

2. サーバー側（dashboard-server）
   - ロボットの状態表示
   - ロボットへの操作指示
   - クラウド上のDockerコンテナとして実行

### アーキテクチャ図

```mermaid
graph TB
    subgraph "開発環境"
        Dev[開発者]
        LocalDocker[ローカルDocker]
    end

    subgraph "Azure"
        ACR[Azure Container Registry]
        WebApp[Azure Web App for Container]
        Webhook[Webhook]
    end

    subgraph "ロボット"
        ROS[ROS]
        ClientDocker[Clientコンテナ]
    end

    subgraph "運営"
        PC[PC]
        Smartphone[スマートフォン]
        WSBrowser[WebSocket Browser]
    end

    Dev -->|Dockerイメージをpush| LocalDocker
    LocalDocker -->|イメージをpush| ACR
    ACR -->|イメージ変更を通知| Webhook
    Webhook -->|自動デプロイ| WebApp
    ACR -->|イメージをpull| WebApp
    ACR -->|イメージをpull| ClientDocker
    ROS -->|起動| ClientDocker
    ClientDocker -->|HTTPロングポーリング| WebApp
    PC -->|HTTP接続| WebApp
    Smartphone -->|HTTP接続| WebApp
    WSBrowser -->|WebSocket接続| WebApp
    PC -->|UI表示| WSBrowser
    Smartphone -->|UI表示| WSBrowser

    classDef azure fill:#0072C6,stroke:#fff,stroke-width:2px,color:#fff;
    class ACR,WebApp,Blob,Webhook azure;
    classDef ws fill:#4CAF50,stroke:#fff,stroke-width:2px,color:#fff;
    class WSBrowser ws;
```

## 通信フロー

### ブラウザ - サーバー間通信（WebSocket）

```mermaid
sequenceDiagram
    participant Browser
    participant Server

    Browser->>Server: WebSocket接続確立
    
    loop WebSocket通信
        Server->>Browser: ロボット状態更新通知
        Browser->>Server: コマンド送信
        Server->>Browser: コマンド実行結果通知
    end

    Note over Browser,Server: 接続が切れた場合は自動再接続
```

### ロボット - サーバー間通信（HTTPロングポーリング）

```mermaid
sequenceDiagram
    participant Robot
    participant Server

    Note over Robot,Server: OAuth2.0による認証

    loop ロングポーリング
        Robot->>Server: GET /poll/{client_id}
        alt コマンドあり
            Server-->>Robot: コマンド送信
            Robot->>Robot: コマンド実行
            Robot->>Server: POST /send/{client_id} (実行結果)
        else コマンドなし
            Server-->>Robot: タイムアウトまで待機
        end
    end

    Note over Robot,Server: 接続が切れた場合は再接続してポーリング再開
```

### 通信プロトコル

1. ブラウザ - サーバー間（WebSocket）
   - リアルタイムな状態更新とコマンド送信
   - 自動再接続機能あり
   - JWT認証による接続確立

2. ロボット - サーバー間（HTTPロングポーリング）
   - 定期的なポーリングによるコマンド取得
   - OAuth2.0による認証
   - コマンド実行結果の送信

## 技術スタック

- 実装言語：Python
- Webフレームワーク：FastAPI
- コンテナ化：Docker
- クラウド環境：Azure（Web App for Containers）
- 認証方式：
  - API認証：APIキー認証
  - 管理画面：ID/パスワード認証

## セキュリティ

### API認証（OAuth 2.0）

- Client Credentials Flowを使用
- クライアントIDとシークレットによる認証
- JWTトークンの発行（有効期限付き）
- APIキーによる認証

### ユーザー認証（JWT）

- JWTベースのセッション管理
- パスワードのbcrypt暗号化
- セッションタイムアウト機能（環境変数で設定可能）
- クッキーベースのトークン管理
  - HTTPOnly: false（WebSocket接続のため）
  - Secure: 環境に応じて設定
  - SameSite: Lax
- ユーザー管理（JSONファイルベース）

### セキュリティ対策

- トークンの有効期限管理
- パスワードの安全な暗号化（bcrypt）
- セッションタイムアウトによる自動ログアウト
- クロスサイトリクエストフォージェリ（CSRF）対策
- 適切なエラーハンドリングとログ記録 