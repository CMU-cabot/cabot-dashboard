from fastapi import Depends, Cookie, HTTPException, Header
from fastapi.security import APIKeyHeader
from typing import Optional

from app.services.auth import AuthService
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.config import settings
from app.utils.logger import logger
from app.services.robot_manager import RobotManager

# シングルトンインスタンスの作成
auth_service = AuthService()
robot_state_manager = RobotStateManager()
command_queue_manager = CommandQueueManager()

# APIキー認証のヘッダー設定
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    """APIキーの検証"""
    if api_key == settings.api_key:
        return api_key
    logger.warning(f"Invalid API key attempt: {api_key}")
    raise HTTPException(
        status_code=403,
        detail="Invalid API key"
    )

async def get_current_user(
    session_token: Optional[str] = Cookie(None)
) -> str:
    """現在のユーザーを取得"""
    user_id = auth_service.validate_session(session_token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user_id

def get_auth_service() -> AuthService:
    """認証サービスのインスタンスを取得"""
    return auth_service

def get_robot_state_manager():
    """RobotStateManagerのインスタンスを取得"""
    return robot_state_manager

def get_robot_manager():
    """後方互換性のために残す（非推奨）"""
    return robot_state_manager

def get_command_queue_manager():
    """CommandQueueManagerのインスタンスを取得"""
    return command_queue_manager    

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    # デバッグログを追加
    logger.debug(f"Verifying API key: {x_api_key}")
    logger.debug(f"Expected API key: {settings.api_key}")
    
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return x_api_key