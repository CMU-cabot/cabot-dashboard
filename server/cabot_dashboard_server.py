from fastapi import FastAPI, Depends, HTTPException, status,Cookie, Request, Response, Form
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

def setup_logger():
    log_level = os.environ.get('CABOT_DASHBOARD_LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.handlers.clear()

    log_to_file = os.environ.get('CABOT_DASHBOARD_LOG_TO_FILE', 'false').lower() == 'true'
    handler = logging.FileHandler(os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'server.log')) if log_to_file else logging.StreamHandler()

    handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(handler)

    return logger

logger = setup_logger()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

API_KEY = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

security = HTTPBasic()

SESSION_TIMEOUT = int(os.getenv("CABOT_DASHBOARD_SESSION_TIMEOUT", 1800))

with open("users.json") as f:
    users = json.load(f)["users"]

sessions = {}

class User(BaseModel):
    username: str
    password: str

def get_current_user(session_token: str = Cookie(None)):
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id, timestamp = sessions[session_token]
    if time.time() - timestamp > SESSION_TIMEOUT:
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    return user_id

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
    raise HTTPException(status_code=403, detail="Invalid API key")

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
connected_cabots = {}
cabot_commands = {}

@app.post("/send/{client_id}")
async def send_message(client_id: str, message: Dict[str, str], api_key: str = Depends(get_api_key)):
    try:
        message_text = message['message']
        message_queue.add_message(f"Rabot {client_id}: {message_text}")
        if client_id in connected_cabots:
            connected_cabots[client_id]["message"] = message_text
        return {"status": "Message received"}
    except Exception as e:
        logger.error(f"Error occurred while processing message from {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/receive")
async def receive_messages(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    
    serializable_cabots = [
        {
            "id": client_id,
            "last_poll": convert_datetime(cabot_info.get("last_poll", "Unknown")),
            "message": cabot_info.get("message", "")
        }
        for client_id, cabot_info in connected_cabots.items()
        if client_id != "dashboard"
    ]
    
    return JSONResponse(content={"cabots": serializable_cabots}, status_code=200)

def convert_datetime(dt):
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)

@app.post("/connect/{client_id}")
async def connect(client_id: str, api_key: str = Depends(get_api_key)):
    try:
        connected_cabots[client_id] = {
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
        connected_cabots.pop(client_id, None)
    logger.info(f"Client {client_id} disconnected")
    return {"status": "Disconnected"}

@app.get("/connected_cabots")
async def get_connected_cabots(api_key: str = Depends(get_api_key)):
    return {
        "cabots": [
            {
                "id": cabot_id,
                "last_poll": cabot_info["last_poll"].isoformat(),
                "message": cabot_info["message"]
            }
            for cabot_id, cabot_info in connected_cabots.items()
        ]
    }

command_queues = {}

@app.post("/send_command/{cabot_id}")
async def send_command(cabot_id: str, command: dict, api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    
    if cabot_id not in connected_cabots:
        raise HTTPException(status_code=404, detail="Specified cabot is not connected")
    
    cabot_commands[cabot_id] = command['command']
    print(f"Command queued for cabot {cabot_id}: {command['command']}")
    return {"status": "success", "message": f"Command queued for cabot {cabot_id}"}

@app.get("/poll/{cabot_id}")
async def poll(cabot_id: str, api_key: str = Depends(get_api_key)):
    if cabot_id not in connected_cabots:
        raise HTTPException(status_code=404, detail="Rabot not connected")

    connected_cabots[cabot_id]["last_poll"] = datetime.now()
    
    if cabot_id in cabot_commands:
        command = cabot_commands.pop(cabot_id)
        print(f"Sending command to cabot {cabot_id}: {command}")
        return JSONResponse(content={"message": command})
    
    return JSONResponse(content={"message": None})

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, session_token: str = Cookie(None)):
    if session_token and session_token in sessions:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.get("/health")
async def health_check(request: Request):
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)