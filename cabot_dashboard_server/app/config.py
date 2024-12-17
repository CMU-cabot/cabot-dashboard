from typing import Dict
import os
import json
from pydantic import BaseSettings

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
    api_key: str = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
    session_timeout: int = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
    max_robots: int = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
    max_messages: int = 100
    polling_timeout: float = float(os.getenv("CABOT_DASHBOARD_POLL_TIMEOUT", 240))
    debug_mode: bool = os.getenv("CABOT_DASHBOARD_DEBUG_MODE", "false").lower() == "true"
    allowed_cabot_ids: str = os.getenv('CABOT_DASHBOARD_ALLOWED_CABOT_IDS', '')
    access_token_expire_minutes: int = int(os.getenv("CABOT_DASHBOARD_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    jwt_secret_key: str = os.getenv("CABOT_DASHBOARD_JWT_SECRET_KEY", "your-jwt-secret-key-here")
    algorithm: str = "HS256"
    client_config: ClientConfig = ClientConfig()

    @property
    def allowed_cabot_id_list(self) -> set:
        return set(filter(None, self.allowed_cabot_ids.split(',')))

    class Config:
        env_prefix = "CABOT_DASHBOARD_"

settings = Settings()