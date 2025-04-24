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
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")
docker_hub_service = DockerHubService()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service),
    robot_manager: RobotStateManager = Depends(get_robot_state_manager)
):
    try:
        logger.info(f"Accessing dashboard with session_token: {session_token[:10] if session_token else 'None'}...")
        
        if not session_token:
            logger.warning("No session token provided")
            return RedirectResponse(url="/login", status_code=303)
            
        is_valid = await auth_service.validate_token(session_token)
        logger.info(f"Token validation result: {is_valid}")
        
        if not is_valid:
            logger.warning("Invalid or expired token")
            return RedirectResponse(url="/login", status_code=303)

        user = await auth_service.get_current_user_from_token(session_token)
        if not user:
            logger.warning("User not found from token")
            return RedirectResponse(url="/login", status_code=303)

        docker_versions = docker_hub_service.get_all_cached_data()
        robots = robot_manager.get_connected_cabots_list()
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "base_url": request.base_url,
                "debug_mode": settings.debug_mode,
                "default_site_repo": settings.default_site_repo,
                "user": user.username,
                "docker_versions": docker_versions,
                "robots": robots,
                "total_robots": len(robots)
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard_page: {str(e)}")
        return RedirectResponse(url="/login", status_code=303)

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
        logger.error(f"Unexpected error in dashboard_page: {str(e)}")
        return RedirectResponse(url="/login")

@router.post("/send_command/{robot_id}")
async def send_command(
    robot_id: str,
    command: Dict,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service),
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager)
):
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

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token or not await auth_service.validate_token(token):
            await websocket.close(code=4001)  # Unauthorized
            return

        await websocket_manager.connect(websocket)
        
        # Send initial robot state
        cabot_list = robot_manager.get_connected_cabots_list()
        await websocket_manager.broadcast({
            "type": "robot_state",
            "cabots": cabot_list,
            "messages": robot_manager.get_messages(limit=100)
        })

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "refresh":
                # Send updated robot state
                await websocket_manager.broadcast({
                    "type": "robot_state",
                    "cabots": robot_manager.get_connected_cabots_list(),
                    "messages": robot_manager.get_messages(limit=100)
                })
            elif data.get("type") == "command":
                cabot_id = data.get("cabotId")
                command_data = data.get("command")
                command_option = data.get("commandOption", {})
                if cabot_id and command_data:
                    if cabot_id not in robot_manager.connected_cabots:
                        logger.error(f"Robot {cabot_id} is not connected")
                        continue
                    system_status = robot_manager.connected_cabots[cabot_id].get("system_status", "unknown")
                    if command_data not in ["get-image-tags", "get-env", "ros_stop"] and system_status not in ["inactive", "failed", "unknown"]:
                        logger.info(f"Command {command_data} not allowed in status {system_status}")
                        continue
                    try:
                        await command_queue_manager.initialize_client(cabot_id)
                        command_mapping = {
                            'ros_start': 'ros-start',
                            'ros_stop': 'ros-stop',
                            'power_off': 'system-poweroff',
                            'reboot': 'system-reboot',
                            'software_update': 'software_update'
                        }
                        formatted_command = {
                            'command': command_mapping.get(command_data, command_data),
                            'commandOption': command_option
                        }
                        logger.info(f"Command added to queue for {cabot_id}: {formatted_command}")
                        await command_queue_manager.add_command(cabot_id, formatted_command)
                    except Exception as e:
                        logger.error(f"Error adding command to queue for {cabot_id}: {e}")
            elif data.get("type") == "refresh_tags":
                response = await websocket_manager.handle_refresh_tags(data)
                await websocket.send_json(response)
            elif data.get("type") == "update_image_name":
                response = await websocket_manager.handle_update_image_name(data)
                await websocket.send_json(response)
            elif data.get("type") == "refresh_site":
                response = await websocket_manager.handle_refresh_site(data)
                await websocket.send_json(response)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        try:
            if websocket in websocket_manager.active_connections:
                websocket_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error during websocket cleanup: {str(e)}")