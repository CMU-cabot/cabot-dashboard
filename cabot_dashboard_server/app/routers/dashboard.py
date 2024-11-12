from fastapi import APIRouter, Depends, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.auth import AuthService
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.dependencies import get_auth_service, get_api_key, get_robot_manager, get_command_queue_manager, get_robot_state_manager
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
    """Display dashboard page"""
    try:
        if not session_token or not auth_service.validate_session(session_token, timeout=3600):
            return RedirectResponse(url="/login")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "base_url": request.base_url,
                "api_key": settings.api_key  # Get API key directly from settings
            }
        )
    except ValueError:
        return RedirectResponse(url="/login")

# API Endpoints
@router.get("/api/dashboard/status")
async def get_dashboard_status(
    robot_manager = Depends(get_robot_manager),
    api_key: str = Depends(get_api_key)
):
    """Get dashboard status information"""
    return {
        "robots": robot_manager.get_robot_info(),
        "messages": robot_manager.messages
    }

@router.get("/receive")
async def receive_updates(
    api_key: str = Depends(get_api_key),
    robot_manager = Depends(get_robot_manager)
):
    """Get robot information and message updates"""
    try:
        robot_info = robot_manager.get_robot_info()
        return {
            "robots": robot_info,
            "messages": robot_manager.messages,
            "events": []
        }
    except Exception as e:
        logger.error(f"Error in receive_updates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/connected_cabots")
async def get_connected_cabots(
    api_key: str = Depends(get_api_key),
    robot_manager = Depends(get_robot_manager)
):
    """Get list of connected CaBots"""
    try:
        connected_cabot_list = robot_manager.get_connected_cabots_list()
        return {"cabots": connected_cabot_list}
    except Exception as e:
        logger.error(f"Error in get_connected_cabots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/send_command/{robot_id}")
async def send_command(
    robot_id: str,
    command: Dict,
    robot_manager: RobotStateManager = Depends(get_robot_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    api_key: str = Depends(get_api_key)
):
    try:
        # Check if client is connected
        if robot_id not in robot_manager.connected_cabots:
            raise HTTPException(
                status_code=404,
                detail=f"Robot {robot_id} is not connected"
            )

        # Initialize command queue if not already initialized
        await command_queue_manager.initialize_client(robot_id)
        
        # Send command
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
    """Get message history"""
    return robot_state_manager.get_messages(limit)