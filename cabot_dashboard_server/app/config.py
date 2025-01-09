from pydantic import BaseSettings
import os

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