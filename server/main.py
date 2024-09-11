from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Dict
from datetime import datetime
import asyncio
import logging
import sys
import os

def setup_logger():
    log_level = os.environ.get('CABOT_DASHBOARD_LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.handlers.clear()

    log_to_file = os.environ.get('CABOT_DASHBOARD_LOG_TO_FILE', 'false').lower() == 'true'
    if log_to_file:
        handler = logging.FileHandler(os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'server.log'))
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(handler)

    return logger

logger = setup_logger()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

API_KEY = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            raise

app.add_middleware(ErrorLoggingMiddleware)

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    logger.warning(f"Invalid API key attempt: {api_key}")
    raise HTTPException(status_code=403, detail="Could not validate API Key")

class MessageQueue:
    def __init__(self):
        self.messages: List[str] = []

    def add_message(self, message: str):
        self.messages.append(message)

    def get_messages(self):
        messages = self.messages.copy()
        self.messages.clear()
        return messages

message_queue = MessageQueue()
connected_robots = {}
robot_commands = {}

@app.post("/send/{client_id}")
async def send_message(client_id: str, message: Dict[str, str], api_key: str = Depends(get_api_key)):
    try:
        message_text = message['message']
        message_queue.add_message(f"Robot {client_id}: {message_text}")
        if client_id in connected_robots:
            connected_robots[client_id]["message"] = message_text
        return {"status": "Message received"}
    except Exception as e:
        logger.error(f"Error occurred while processing message from {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/receive")
async def receive_messages(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API key")
    
    serializable_robots = [
        {
            "id": client_id,
            "last_poll": convert_datetime(robot_info.get("last_poll", "Unknown")),
            "message": robot_info.get("message", "")
        }
        for client_id, robot_info in connected_robots.items()
        if client_id != "dashboard"
    ]
    
    return JSONResponse(content={"robots": serializable_robots}, status_code=200)

def convert_datetime(dt):
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)

@app.post("/connect/{client_id}")
async def connect(client_id: str, api_key: str = Depends(get_api_key)):
    try:
        connected_robots[client_id] = {
            "last_poll": datetime.now(),
            "message": ""
        }
        logger.info(f"Client {client_id} connected")
        return {"status": "Connected"}
    except Exception as e:
        logger.error(f"Error connecting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/disconnect/{client_id}")
async def disconnect(client_id: str, api_key: str = Depends(get_api_key)):
    if client_id != "dashboard":
        connected_robots.pop(client_id, None)
    logger.info(f"Client {client_id} disconnected")
    return {"status": "Disconnected"}

@app.get("/connected_robots")
async def get_connected_robots(api_key: str = Depends(get_api_key)):
    return {
        "robots": [
            {
                "id": robot_id,
                "last_poll": robot_info["last_poll"].isoformat(),
                "message": robot_info["message"]
            }
            for robot_id, robot_info in connected_robots.items()
        ]
    }

command_queues = {}

@app.post("/send_command/{robot_id}")
async def send_command(robot_id: str, command: dict, api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API key")
    
    if robot_id not in connected_robots:
        raise HTTPException(status_code=404, detail="Specified robot is not connected")
    
    robot_commands[robot_id] = command['command']
    print(f"Command queued for robot {robot_id}: {command['command']}")
    return {"status": "success", "message": f"Command queued for robot {robot_id}"}

@app.get("/poll/{robot_id}")
async def poll(robot_id: str, api_key: str = Depends(get_api_key)):
    if robot_id not in connected_robots:
        raise HTTPException(status_code=404, detail="Robot not connected")

    connected_robots[robot_id]["last_poll"] = datetime.now()
    
    if robot_id in robot_commands:
        command = robot_commands.pop(robot_id)
        print(f"Sending command to robot {robot_id}: {command}")
        return JSONResponse(content={"message": command})
    
    return JSONResponse(content={"message": None})

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    base_url = request.base_url
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "base_url": base_url,
        "api_key": API_KEY
    })

@app.get("/health")
async def health_check(request: Request):
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)