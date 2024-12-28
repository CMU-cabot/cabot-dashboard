from fastapi import APIRouter, Depends, Request, Cookie, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.auth import AuthService
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.dependencies import get_auth_service, get_api_key, get_command_queue_manager, get_robot_state_manager
from app.utils.logger import logger
from app.config import settings
from typing import Dict, List
from app.services.websocket import manager as websocket_manager
from app.services.docker_hub import DockerHubService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
docker_hub_service = DockerHubService()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        if not session_token or not auth_service.validate_session(session_token, timeout=3600):
            return RedirectResponse(url="/login")

        docker_versions = docker_hub_service.get_all_cached_data()
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "base_url": request.base_url,
                "api_key": settings.api_key,
                "debug_mode": settings.debug_mode,
                "user": "user1",  # TODO 一時的な対処
                "docker_versions": docker_versions
            }
        )
    except ValueError:
        return RedirectResponse(url="/login")

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

        logger.info(f"Command sent to {robot_id}: {command}")
        await command_queue_manager.initialize_client(robot_id)
        await command_queue_manager.add_command(robot_id, command)        
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

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager)
):
    await websocket_manager.connect(websocket)
    try:
        cabot_list = robot_manager.get_connected_cabots_list()
        await websocket_manager.broadcast({
            "cabots": cabot_list,
            "messages": robot_manager.get_messages(limit=100)
        })
        
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "refresh":
                await websocket_manager.broadcast({
                    "cabots": robot_manager.get_connected_cabots_list(),
                    "messages": robot_manager.get_messages(limit=100)
                })
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        websocket_manager.disconnect(websocket)

@router.post("/api/refresh-tags/{repository}")
async def refresh_tags(repository: str):
    try:
        tags = await docker_hub_service.fetch_tags(repository)
        return {"status": "success", "tags": tags}
    except Exception as e:
        logger.error(f"Failed to fetch tags for {repository}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to fetch tags: {str(e)}"
        }

@router.post("/api/update-image-name/{repository}")
async def update_image_name(repository: str, name: str = Body(..., embed=True)):
    try:
        cached_data = docker_hub_service.get_cached_tags(repository)
        if cached_data is None:
            return {
                "status": "error",
                "message": "Repository not found"
            }
        
        cached_data["name"] = name
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update image name for {repository}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update image name: {str(e)}"
        }