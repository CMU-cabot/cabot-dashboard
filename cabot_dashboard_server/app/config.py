from typing import Dict
import os
import json
import re
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


def extract_cabot_ids(key: str) -> set:
    result = []
    for id in os.getenv(key, "").strip().split(","):
        id = id.strip()
        if id:
            m = re.search(r"[\(\[](.*)[\)\]]", id)
            result.append(m.group(1).strip() if m else id)
    return set(result)


def get_cabot_name_map(key: str) -> dict:
    result = {}
    for name in os.getenv(key, "").strip().split(","):
        name = name.strip()
        if name:
            m = re.search(r"[\(\[](.*)[\)\]]", name)
            if m:
                result[m.group(1).strip()] = name
    return result


class Settings(BaseSettings):
    api_key: str = os.getenv("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
    session_timeout: int = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
    session_secret_key: str = os.getenv("CABOT_DASHBOARD_SESSION_SECRET", "your-secret-key-here")
    use_secure_cookies: bool = os.getenv("CABOT_DASHBOARD_USE_SECURE_COOKIES", "true").lower() == "true"
    max_robots: int = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
    max_messages: int = 100
    polling_timeout: float = float(os.getenv("CABOT_DASHBOARD_POLL_TIMEOUT", 240))
    disconnect_detectioin_second: float = float(os.getenv("CABOT_DASHBOARD_DISCONNECT_DETECTION_SECOND", 10 * 60))
    debug_mode: bool = os.getenv("CABOT_DASHBOARD_DEBUG_MODE", "false").lower() == "true"
    allowed_cabot_id_list: set = extract_cabot_ids('CABOT_DASHBOARD_ALLOWED_CABOT_IDS')
    cabot_name_map: dict = get_cabot_name_map('CABOT_DASHBOARD_ALLOWED_CABOT_IDS')
    access_token_expire_minutes: int = int(os.getenv("CABOT_DASHBOARD_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    jwt_secret_key: str = os.getenv("CABOT_DASHBOARD_JWT_SECRET_KEY", "your-jwt-secret-key-here")
    default_site_repo = os.getenv("CABOT_DASHBOARD_DEFAULT_SITE_REPO", "")
    algorithm: str = "HS256"
    client_config: ClientConfig = ClientConfig()

    # CORS settings
    cors_origins: List[str] = os.getenv("CABOT_DASHBOARD_CORS_ORIGINS", "http://localhost:8000").split(",")
    cors_methods: List[str] = os.getenv("CABOT_DASHBOARD_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    cors_headers: List[str] = os.getenv("CABOT_DASHBOARD_CORS_HEADERS", "Accept,Authorization,Content-Type,X-Requested-With").split(",")
    microsoft_client_id: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_CLIENT_ID", "")
    microsoft_client_secret: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_CLIENT_SECRET", "")
    microsoft_tenant_id: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_TENANT_ID", "")
    microsoft_redirect_path: str = os.getenv("CABOT_DASHBOARD_MICROSOFT_REDIRECT_PATH", "/auth/microsoft/callback")

    class Config:
        env_prefix = "CABOT_DASHBOARD_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
