from fastapi import Depends, Cookie, HTTPException, Header
from fastapi.security import APIKeyHeader
from typing import Optional

from app.services.auth import AuthService
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.config import settings
from app.utils.logger import logger

# Create singleton instances
auth_service = AuthService()
robot_state_manager = RobotStateManager()
command_queue_manager = CommandQueueManager()

# API key authentication header settings
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
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
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    user = await auth_service.get_current_user_from_token(session_token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user.username

def get_auth_service() -> AuthService:
    return auth_service

def get_robot_state_manager():
    return robot_state_manager

def get_command_queue_manager():
    return command_queue_manager    

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    logger.debug(f"Verifying API key: {x_api_key}")
    logger.debug(f"Expected API key: {settings.api_key}")
    
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return x_api_key