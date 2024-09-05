# This code manages WebSocket connections and broadcasts messages from robots.

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from typing import List
import websockets
import logging
import sys
import os

app = FastAPI()

# Log configuration (same as before)
def setup_logger():
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    if os.environ.get('LOG_TO_FILE', 'false').lower() == 'true':
        log_file = os.environ.get('LOG_FILE', 'robot.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(file_handler)
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(stream_handler)

    return logger

logger = setup_logger()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            logger.warning(f"WebSocket {websocket} was not in active_connections")

    async def broadcast(self, message: str):
        logger.info(f"Broadcasting message: {message}")
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                logger.debug(f"Sent message to {connection}")
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Connection closed for {connection}")
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"An error occurred during broadcast: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        if client_id == "dashboard":
            logger.info("Dashboard connected")
            while True:
                try:
                    # Dashboard only receives
                    await websocket.receive_text()
                except asyncio.TimeoutError:
                    pass
        else:
            logger.info(f"Robot {client_id} connected")
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                    await manager.broadcast(f"Robot {client_id}: {data}")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout for Robot {client_id}")
                    await manager.broadcast(f"Timeout for Robot {client_id}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for client {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client {client_id} disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)