from fastapi import APIRouter, Depends, HTTPException, Response, Request
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.dependencies import (
    get_api_key,
    get_command_queue_manager,
    get_robot_state_manager
)
from app.utils.logger import logger
import asyncio
from typing import Optional
import json

router = APIRouter(tags=["client"])

@router.post("/connect/{client_id}")
async def connect(
    client_id: str,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    api_key: str = Depends(get_api_key)
):
    try:
        robot_manager.update_robot_state(client_id, {
            "status": "connected",
            "message": f"{client_id} connected"
        })
        
        await command_queue_manager.initialize_client(client_id)
        logger.info(f"Client {client_id} connected")
        return {"status": "Connected"}
    except Exception as e:
        logger.error(f"Error connecting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/poll/{client_id}")
async def poll(
    request: Request,
    client_id: str,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    api_key: str = Depends(get_api_key)
):
    if client_id not in robot_manager.connected_cabots:
        logger.warning(f"Poll attempted for disconnected client {client_id}")
        raise HTTPException(status_code=404, detail="Robot not connected")
    try:
        body = await request.json()
        system_status = body.get("cabot_system_status", "unknown")
        logger.debug(f"Received poll request from {client_id} with system_status: {system_status}")

        state = {
            "status": "connected",
            "system_status": system_status,
            "message": ""
        }
        robot_manager.update_robot_state(client_id, state)

        result = await command_queue_manager.wait_for_update(client_id)
        return result
    except asyncio.TimeoutError:
        return Response(status_code=204)
    except Exception as e:
        logger.error(f"Error in poll for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        state = {
            "status": "disconnected",
            "system_status": "unknown",
            "message": ""
        }
        robot_manager.update_robot_state(client_id, state)

@router.post("/send/{client_id}")
async def send_status(
    client_id: str,
    status: dict,
    robot_manager: RobotStateManager = Depends(get_robot_state_manager)
):
    if client_id not in robot_manager.connected_cabots:
        logger.warning(f"Send status attempted for disconnected client {client_id}")
        raise HTTPException(status_code=404, detail="Specified cabot is not connected")
    
    try:
        logger.info(f"Received from {client_id} status: {json.dumps(status, indent=2)}")
        
        # Get message type and status directly from the status object
        msg_type = status.get("type", "plain")
        msg_status = status.get("status", "info")
        msg_content = status.get("message", "")

        # Handle different message types
        if msg_type == "image_tags":
            if msg_status == "success":
                # Update robot images with the tags data
                tags = status.get("tags", {})
                logger.info(f"Updating image tags for {client_id}: {json.dumps(tags, indent=2)}")
                robot_manager.update_robot_images(client_id, tags)
                robot_manager.update_robot_message(client_id, "Image tags updated successfully", "success")
            elif msg_status == "error":
                robot_manager.update_robot_message(client_id, msg_content, "error")
            else:
                robot_manager.update_robot_message(client_id, msg_content, msg_status)
        elif msg_type == "software_update":
            robot_manager.update_robot_message(client_id, msg_content, msg_status)
        elif msg_type == "command":
            robot_manager.update_robot_message(client_id, msg_content, msg_status)
        else:
            # If no type is specified, treat the entire message as a plain text message
            if "message" in status:
                robot_manager.update_robot_message(client_id, msg_content, msg_status)
            else:
                robot_manager.update_robot_message(client_id, str(status), "info")

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating status for {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")