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
        if not session_token or not await auth_service.validate_token(session_token):
            return RedirectResponse(url="/login", status_code=303)

        user = await auth_service.get_current_user_from_token(session_token)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "base_url": request.base_url,
                "debug_mode": settings.debug_mode,
                "user": "user1"  # TODO 一時的な対処
            }
        )
    except ValueError:
        return RedirectResponse(url="/login")

@router.get("/receive")
async def receive_updates(
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service),
    robot_manager = Depends(get_robot_state_manager)
):
    if not session_token or not await auth_service.validate_token(session_token):
        raise HTTPException(status_code=401, detail="Invalid session")

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
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service),
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager)
):
    try:
        if not session_token or not await auth_service.validate_token(session_token):
            raise HTTPException(status_code=403, detail="Invalid session")

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