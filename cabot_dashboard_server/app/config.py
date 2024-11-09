from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    api_key: str = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
    session_timeout: int = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
    max_robots: int = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
    max_messages: int = 100
    polling_timeout: float = float(os.getenv("CABOT_DASHBOARD_POLL_TIMEOUT", 240))

    class Config:
        env_prefix = "CABOT_DASHBOARD_"

settings = Settings()