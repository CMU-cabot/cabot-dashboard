from pydantic import BaseSettings
import os
from typing import List

class Settings(BaseSettings):
    api_key: str = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
    session_timeout: int = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
    max_robots: int = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
    max_messages: int = 100
    polling_timeout: float = float(os.getenv("CABOT_DASHBOARD_POLL_TIMEOUT", 240))
    debug_mode: bool = os.getenv("CABOT_DASHBOARD_DEBUG_MODE", "false").lower() == "true"
    allowed_cabot_ids: str = os.getenv('CABOT_DASHBOARD_ALLOWED_CABOT_IDS', '')
    timezone: str = os.getenv('CABOT_DASHBOARD_TIMEZONE', 'Asia/Tokyo')

    # CORS settings
    cors_origins: List[str] = os.getenv("CABOT_DASHBOARD_CORS_ORIGINS", "http://localhost:8000").split(",")
    cors_methods: List[str] = os.getenv("CABOT_DASHBOARD_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    cors_headers: List[str] = os.getenv("CABOT_DASHBOARD_CORS_HEADERS", "Accept,Authorization,Content-Type,X-Requested-With").split(",")

    @property
    def allowed_cabot_id_list(self) -> set:
        return set(filter(None, self.allowed_cabot_ids.split(',')))

    class Config:
        env_prefix = "CABOT_DASHBOARD_"

settings = Settings()