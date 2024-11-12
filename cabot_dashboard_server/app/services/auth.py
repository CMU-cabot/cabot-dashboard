import bcrypt
import secrets
import time
from typing import Dict, Tuple
import json
from app.utils.logger import logger

class AuthService:
    def __init__(self):
        self.sessions: Dict[str, Tuple[str, float]] = {}
        with open("users.json") as f:
            self.users = json.load(f)["users"]

    def validate_user(self, username: str, password: str) -> bool:
        for user in self.users:
            if user["id"] == username and bcrypt.checkpw(
                password.encode('utf-8'), 
                user["password_hash"].encode('utf-8')
            ):
                return True
        return False

    def create_session(self, username: str) -> str:
        session_token = secrets.token_urlsafe(16)
        self.sessions[session_token] = (username, time.time())
        return session_token

    def validate_session(self, session_token: str, timeout: int) -> str:
        if not session_token or session_token not in self.sessions:
            raise ValueError("Authentication required")
        
        user_id, timestamp = self.sessions[session_token]
        if time.time() - timestamp > timeout:
            del self.sessions[session_token]
            raise ValueError("Session expired")
            
        return user_id

    def remove_session(self, session_token: str) -> None:
        """Remove the session"""
        if session_token in self.sessions:
            del self.sessions[session_token]