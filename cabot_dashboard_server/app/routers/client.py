from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import APIKeyHeader
from app.services.robot_state import RobotStateManager
from app.services.command_queue import CommandQueueManager
from app.dependencies import (
    get_api_key,
    get_robot_manager,
    get_command_queue_manager,
    get_robot_state_manager
)
from app.utils.logger import logger
from datetime import datetime
import asyncio

router = APIRouter(tags=["client"])

# 依存性の注入
robot_state_manager = RobotStateManager()
command_queue_manager = CommandQueueManager()

@router.post("/connect/{client_id}")
async def connect(
    client_id: str,
    robot_manager: RobotStateManager = Depends(get_robot_manager),
    api_key: str = Depends(get_api_key)
):
    try:
        # 接続時に初期状態を設定
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

@router.post("/send_command/{cabot_id}")
async def send_command(
    cabot_id: str,
    command: dict,
    api_key: str = Depends(get_api_key)
):
    try:
        if cabot_id not in robot_state_manager.connected_cabots:
            raise HTTPException(status_code=404, detail="Specified cabot is not connected")
        
        await command_queue_manager.add_command(cabot_id, command)
        return {"status": "success", "message": f"Command queued for cabot {cabot_id}"}
    except ValueError as e:
        logger.error(f"Invalid command format for cabot {cabot_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing command for cabot {cabot_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/poll/{client_id}")
async def poll(
    client_id: str,
    robot_manager: RobotStateManager = Depends(get_robot_manager),
    command_queue_manager: CommandQueueManager = Depends(get_command_queue_manager),
    api_key: str = Depends(get_api_key)
):
    logger.debug(f"[POLL] Starting poll for {client_id}")
    logger.debug(f"[POLL] Connected robots: {robot_manager.connected_cabots}")
    
    try:
        if client_id not in robot_manager.connected_cabots:
            logger.warning(f"[POLL] Robot {client_id} not found in connected_cabots")
            raise HTTPException(status_code=404, detail="Robot not connected")

        try:
            result = await command_queue_manager.wait_for_update(client_id)
            logger.debug(f"[POLL] Got result for {client_id}: {result}")
            return result
        except asyncio.TimeoutError:
            logger.debug(f"[POLL] Poll timeout for {client_id}")
            return Response(status_code=204)  # No Content
            
    except Exception as e:
        logger.error(f"[POLL] Error in poll for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send/{client_id}")
async def send_status(
    client_id: str,
    status: dict,
    robot_state_manager: RobotStateManager = Depends(get_robot_state_manager)
):
    if client_id not in robot_state_manager.connected_cabots:
        raise HTTPException(status_code=404, detail="Specified cabot is not connected")
    
    try:
        message = status.get("message", "")
        robot_state_manager.update_client_status(client_id, message)
        logger.info(f"Received status from {client_id}: {message}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating status for {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")