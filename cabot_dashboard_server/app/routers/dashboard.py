from fastapi import APIRouter, Depends, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.auth import AuthService
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.dependencies import get_auth_service, get_api_key, get_command_queue_manager, get_robot_state_manager
from app.utils.logger import get_logger
from app.config import settings
from typing import Dict

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        logger.info(f"Accessing dashboard with session_token: {session_token[:10] if session_token else 'None'}...")
        
        if not session_token:
            logger.warning("No session token provided")
            return RedirectResponse(url="/login")
            
        is_valid = auth_service.validate_session(session_token, timeout=3600)
        logger.info(f"Session validation result: {is_valid}")
        
        if not is_valid:
            logger.warning("Invalid or expired session token")
            return RedirectResponse(url="/login")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "base_url": request.base_url,
                "api_key": settings.api_key,
                "debug_mode": settings.debug_mode,
                "user": "user1"  # TODO ユーザ名となるものを表示する
            }
        )
    except ValueError as ve:
        logger.error(f"ValueError in dashboard_page: {str(ve)}")
        return RedirectResponse(url="/login")
    except Exception as e:
        logger.error(f"Unexpected error in dashboard_page: {str(e)}")
        return RedirectResponse(url="/login")

@router.get("/receive")
async def receive_updates(
    api_key: str = Depends(get_api_key),
    robot_manager = Depends(get_robot_state_manager)
):
    try:
        connected_cabot_list = robot_manager.get_connected_cabots_list()
        return {
            "messages": robot_manager.messages,
            "events": [],
            "cabots": connected_cabot_list
        }
    except Exception as e:
        logger.error(f"Error in receive_updates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/send_command/{robot_id}")
async def send_command(
    robot_id: str,
    command: Dict,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    api_key: str = Depends(get_api_key)
):
    try:
        if robot_id not in robot_manager.connected_cabots:
            raise HTTPException(
                status_code=404,
                detail=f"Robot {robot_id} is not connected"
            )

        await command_queue_manager.initialize_client(robot_id)
        await command_queue_manager.add_command(robot_id, command)
        logger.info(f"Command sent to {robot_id}: {command}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error sending command to {robot_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages")
async def get_messages(
    limit: int = 100,
    robot_state_manager: RobotStateManager = Depends(get_robot_state_manager)
):
    return robot_state_manager.get_messages(limit)