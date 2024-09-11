import asyncio
from fastapi import FastAPI, Depends, HTTPException, status, Cookie, Request, Response, Form, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime
import json
import os
import secrets
import time
import logging
import bcrypt
from asyncio import Queue, Event

# Configuration
API_KEY = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
SESSION_TIMEOUT = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))
MAX_ROBOTS = int(os.getenv("CABOT_DASHBOARD_MAX_ROBOTS", 5))
MAX_MESSAGES = 100

# Global variables
connected_cabots: Dict[str, Dict] = {}
command_queues: Dict[str, Queue] = {}
state_update_events: Dict[str, Event] = {}
robot_states: Dict[str, Dict] = {}
messages: List[Dict] = []
sessions: Dict[str, tuple] = {}

# Logger setup
def setup_logger():
    log_level = os.environ.get('CABOT_DASHBOARD_LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.handlers.clear()

    log_to_file = os.environ.get('CABOT_DASHBOARD_LOG_TO_FILE', 'false').lower() == 'true'
    log_file = os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'server.log')
    handler = logging.FileHandler(log_file) if log_to_file else logging.StreamHandler()

    handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(handler)

    return logger

logger = setup_logger()

# FastAPI application configuration
app = FastAPI()
templates = Jinja2Templates(directory="templates")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security = HTTPBasic()

# Load user information
with open("users.json") as f:
    users = json.load(f)["users"]

class User(BaseModel):
    username: str
    password: str

# Authentication related functions
def get_current_user(session_token: str = Cookie(None)):
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id, timestamp = sessions[session_token]
    if time.time() - timestamp > SESSION_TIMEOUT:
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    return user_id

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    logger.warning(f"Invalid API key attempt: {api_key}")
    raise HTTPException(status_code=403, detail="Invalid API key")

# Error handling middleware
class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            raise

app.add_middleware(ErrorLoggingMiddleware)

# Route definitions
@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    for u in users:
        if u["id"] == username and bcrypt.checkpw(password.encode('utf-8'), u["password_hash"].encode('utf-8')):
            session_token = secrets.token_urlsafe(16)
            sessions[session_token] = (username, time.time())
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(key="session_token", value=session_token)
            return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"}, status_code=401)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": current_user,
        "api_key": API_KEY,
        "base_url": request.base_url
    })

@app.post("/logout")
async def logout(response: Response, session_token: str = Cookie(None)):
    if session_token in sessions:
        del sessions[session_token]
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="session_token")
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html>
        <body>
            <h1>Login</h1>
            <form action="/login" method="post">
                <input type="text" name="username" placeholder="Username">
                <input type="password" name="password" placeholder="Password">
                <input type="submit" value="Login">
            </form>
        </body>
    </html>
    """

@app.post("/connect/{client_id}")
async def connect(client_id: str, api_key: str = Depends(get_api_key)):
    try:
        connected_cabots[client_id] = {
            "last_poll": datetime.now(),
            "message": ""
        }
        command_queues[client_id] = Queue()
        state_update_events[client_id] = Event()
        logger.info(f"Client {client_id} connected")
        return {"status": "Connected"}
    except Exception as e:
        logger.error(f"Error connecting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/send_command/{cabot_id}")
async def send_command(cabot_id: str, command: dict, api_key: str = Depends(get_api_key)):
    if cabot_id not in connected_cabots:
        raise HTTPException(status_code=404, detail="Specified cabot is not connected")
    
    await command_queues[cabot_id].put(command['command'])
    state_update_events[cabot_id].set()
    logger.info(f"Command '{command['command']}' added to queue for cabot {cabot_id}")
    return {"status": "success", "message": f"Command queued for cabot {cabot_id}"}

@app.get("/poll/{client_id}")
async def poll(client_id: str, api_key: str = Depends(get_api_key)):
    if client_id not in connected_cabots:
        logger.warning(f"Robot {client_id} not connected")
        raise HTTPException(status_code=404, detail="Robot not connected")

    logger.info(f"Received poll request from {client_id}")
    try:
        result = await wait_for_update(client_id)
        logger.info(f"Sending update to {client_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during polling for {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def wait_for_update(client_id):
    try:
        if not command_queues[client_id].empty():
            command = await command_queues[client_id].get()
            logger.info(f"Retrieved command from queue for {client_id}: {command}")
            return {"type": "command", "data": command}

        await state_update_events[client_id].wait()
        state_update_events[client_id].clear()
        
        if not command_queues[client_id].empty():
            command = await command_queues[client_id].get()
            logger.info(f"Retrieved command from queue for {client_id} after event: {command}")
            return {"type": "command", "data": command}
        
        logger.info(f"State update event received for {client_id}. Current state: {robot_states.get(client_id, {})}")
        return {"type": "state", "data": robot_states.get(client_id, {})}

    except Exception as e:
        logger.error(f"Error while waiting for update for {client_id}: {e}")
        raise

async def update_robot_state(robot_id: str, new_state: dict):
    robot_states[robot_id] = new_state
    state_update_events[robot_id].set()
    logger.info(f"Updated state for robot {robot_id}: {new_state}")

@app.get("/receive")
async def receive_updates(api_key: str = Depends(get_api_key)):
    global messages  # Explicitly use global variable
    try:
        robot_info = []
        for robot_id, info in connected_cabots.items():
            robot_info.append({
                "id": robot_id,
                "last_poll": info["last_poll"].isoformat(),
                "message": info["message"],
                "state": robot_states.get(robot_id, {})
            })
        
        return {
            "robots": robot_info,
            "messages": messages,  # Return stored messages
            "events": []  # Add events here if any
        }
    except Exception as e:
        logger.error(f"Error in receive_updates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, session_token: str = Cookie(None)):
    if session_token and session_token in sessions:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.get("/health")
async def health_check(request: Request):
    return {"status": "OK"}

@app.get("/connected_cabots")
async def get_connected_cabots(api_key: str = Depends(get_api_key)):
    try:
        connected_cabot_list = [
            {
                "id": cabot_id,
                "last_poll": cabot_info["last_poll"].isoformat(),
                "message": cabot_info["message"]
            }
            for cabot_id, cabot_info in connected_cabots.items()
        ]
        
        while len(connected_cabot_list) < MAX_ROBOTS:
            connected_cabot_list.append({
                "id": "Disconnected",
                "last_poll": "N/A",
                "message": ""
            })

        return {"cabots": connected_cabot_list}
    except Exception as e:
        logger.error(f"Error in get_connected_cabots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/send/{client_id}")
async def send_status(client_id: str, status: dict, api_key: str = Depends(get_api_key)):
    global messages  # Explicitly use global variable
    if client_id not in connected_cabots:
        raise HTTPException(status_code=404, detail="Specified cabot is not connected")
    
    message = status.get("message", "")
    connected_cabots[client_id]["message"] = message
    messages.append({"timestamp": datetime.now().isoformat(), "client_id": client_id, "message": message})
    if len(messages) > 100:  # Keep only the latest 100 messages
        messages = messages[-100:]
    
    logger.info(f"Received status from {client_id}: {message}")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)