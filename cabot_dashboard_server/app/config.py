from typing import Dict
import os
import json
from pydantic import BaseSettings
from typing import List

class ClientConfig(BaseSettings):
    # CABOT_DASHBOARD_CLIENTS={"client1": {"secret": "xxx", "name": "robot1"}, "client2": {"secret": "yyy", "name": "robot2"}}
    clients_json: str = os.getenv("CABOT_DASHBOARD_CLIENTS", "{}")

    @property
    def clients(self) -> Dict:
        try:
            return json.loads(self.clients_json)
        except json.JSONDecodeError:
            return {}

class Settings(BaseSettings):
    api_key: str = os.getenv("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
    session_timeout: int = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
    session_secret_key: str = os.getenv("CABOT_DASHBOARD_SESSION_SECRET", "your-secret-key-here")
    use_secure_cookies: bool = os.getenv("CABOT_DASHBOARD_USE_SECURE_COOKIES", "true").lower() == "true"
    max_robots: int = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
    max_messages: int = 100
    polling_timeout: float = float(os.getenv("CABOT_DASHBOARD_POLL_TIMEOUT", 240))
    debug_mode: bool = os.getenv("CABOT_DASHBOARD_DEBUG_MODE", "false").lower() == "true"
    allowed_cabot_ids: str = os.getenv('CABOT_DASHBOARD_ALLOWED_CABOT_IDS', '')
    access_token_expire_minutes: int = int(os.getenv("CABOT_DASHBOARD_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    jwt_secret_key: str = os.getenv("CABOT_DASHBOARD_JWT_SECRET_KEY", "your-jwt-secret-key-here")
    algorithm: str = "HS256"
    client_config: ClientConfig = ClientConfig()
    # timezone: str = os.getenv('CABOT_DASHBOARD_TIMEZONE', 'Asia/Tokyo')

    # CORS settings
    cors_origins: List[str] = os.getenv("CABOT_DASHBOARD_CORS_ORIGINS", "http://localhost:8000").split(",")
    cors_methods: List[str] = os.getenv("CABOT_DASHBOARD_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    cors_headers: List[str] = os.getenv("CABOT_DASHBOARD_CORS_HEADERS", "Accept,Authorization,Content-Type,X-Requested-With").split(",")
    microsoft_client_id: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_CLIENT_ID", "")
    microsoft_client_secret: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_CLIENT_SECRET", "")
    microsoft_tenant_id: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_TENANT_ID", "")
    microsoft_redirect_path: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_REDIRECT_PATH", "/auth/microsoft/callback")

    @property
    def allowed_cabot_id_list(self) -> set:
        return set(filter(None, self.allowed_cabot_ids.split(',')))

    class Config:
        env_prefix = "CABOT_DASHBOARD_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()