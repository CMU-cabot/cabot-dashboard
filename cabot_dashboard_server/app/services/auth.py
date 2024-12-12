import bcrypt
import secrets
import time
from typing import Dict, Tuple
import json
from app.utils.logger import get_logger
from datetime import datetime
import random

class AuthService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.sessions = {}
            self.logger = get_logger(__name__)
            with open("users.json") as f:
                self.users = json.load(f)["users"]
            self.microsoft_users = set()
            self._initialized = True

    def validate_user(self, username: str, password: str) -> bool:
        for user in self.users:
            if user["id"] == username and bcrypt.checkpw(
                password.encode('utf-8'), 
                user["password_hash"].encode('utf-8')
            ):
                return True
        return False

    def create_session(self, email: str) -> str:
        try:
            session_token = self._generate_session_token()
            self.sessions[session_token] = {
                'email': email,
                'created_at': datetime.now()
            }
            self.logger.info(f"Created session for user: {email} with token: {session_token[:10]}...")
            self.logger.info(f"Current sessions: {list(self.sessions.keys())}")
            return session_token
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            raise ValueError("Failed to create session")

    def _generate_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    def validate_session(self, session_token: str, timeout: int = 3600) -> bool:

        # Execute cleanup periodically (e.g., with a 10% probability)
        if random.random() < 0.1:
            self.cleanup_sessions(timeout)
        
        try:
            self.logger.info(f"Validating session token: {session_token[:10]}...")
            
            if not session_token:
                self.logger.warning("No session token provided")
                return False
                
            if session_token not in self.sessions:
                self.logger.warning(f"Session token not found in sessions")
                return False
                
            session_data = self.sessions[session_token]
            created_at = session_data['created_at']
            
            if (datetime.now() - created_at).total_seconds() > timeout:
                self.logger.warning(f"Session expired for token: {session_token[:10]}...")
                del self.sessions[session_token]
                return False
            
            self.logger.info(f"Session validated for user: {session_data.get('email')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating session: {str(e)}")
            return False

    def remove_session(self, session_token: str) -> None:
        """Remove the session"""
        if session_token in self.sessions:
            del self.sessions[session_token]

    def register_microsoft_user(self, email: str) -> None:
        """Register Microsoft authenticated user"""
        self.microsoft_users.add(email)

    def cleanup_sessions(self, timeout: int = 3600) -> None:
        """Delete expired sessions"""
        try:
            now = datetime.now()
            expired_tokens = [
                token for token, data in self.sessions.items()
                if (now - data['created_at']).total_seconds() > timeout
            ]
            
            for token in expired_tokens:
                del self.sessions[token]
            
            if expired_tokens:
                self.logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
                self.logger.debug(f"Remaining active sessions: {len(self.sessions)}")
        except Exception as e:
            self.logger.error(f"Error cleaning up sessions: {str(e)}")