from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings
from app.utils.logger import logger
import json
import bcrypt
from typing import Dict

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class AuthService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            self.oauth2_user_scheme = OAuth2PasswordBearer(tokenUrl="token")
            self.oauth2_client_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")
            with open("users.json") as f:
                self.users = json.load(f)["users"]
            self.microsoft_users = set()  # Store Microsoft authenticated users
            self._initialized = True

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            result = bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            logger.debug(f"Password verification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    def get_user(self, username: str) -> Optional[UserInDB]:
        try:
            logger.debug(f"Looking up user: {username}")
            logger.debug(f"Available users: {[user['id'] for user in self.users]}")
            for user in self.users:
                if user["id"] == username:
                    logger.info(f"User found: {username}")
                    return UserInDB(
                        username=user["id"],
                        hashed_password=user["password_hash"],
                        disabled=False
                    )
            logger.warning(f"User not found: {username}")
            return None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        logger.info(f"Attempting to authenticate user: {username}")
        user = self.get_user(username)
        if not user:
            logger.warning(f"User not found: {username}")
            return None
        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {username}")
            return None
        logger.info(f"Authentication successful for user: {username}")
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
            logger.info(f"Created access token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise

    async def validate_token(self, token: str) -> bool:
        try:
            logger.info(f"Validating token: {token[:10]}...")
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            logger.info(f"Token payload decoded successfully: {payload}")
            return True
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token has expired")
            return False
        except jwt.JWTError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return False

    async def get_current_user_from_token(self, token: str) -> Optional[User]:
        try:
            logger.info(f"Getting user from token: {token[:10]}...")
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            username = payload.get("sub")
            logger.info(f"Username from token: {username}")
            
            if not username:
                logger.warning("No username found in token payload")
                return None
                
            user = self.get_user(username)
            if user:
                logger.info(f"User found: {user.username}")
                return User(username=user.username, disabled=user.disabled)
            else:
                logger.warning(f"User not found for username: {username}")
            return None
        except Exception as e:
            logger.error(f"Error getting user from token: {str(e)}")
            return None

    async def authenticate_client(self, client_id: str, client_secret: str) -> bool:
        clients = settings.client_config.clients
        if client_id not in clients:
            return False
        return clients[client_id]["secret"] == client_secret

    async def create_client_token(self, client_id: str) -> Token:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": client_id, "type": "client"},
            expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")

    def register_microsoft_user(self, email: str) -> None:
        """Register a Microsoft authenticated user"""
        logger.info(f"Registering Microsoft user: {email}")
        self.microsoft_users.add(email)
        # Check if user already exists in users.json
        user_exists = any(user["id"] == email for user in self.users)
        if not user_exists:
            # Add user to users.json with empty password hash (since we use Microsoft auth)
            new_user = {
                "id": email,
                "password_hash": ""  # Empty since we use Microsoft auth
            }
            self.users.append(new_user)
            logger.info(f"Added new Microsoft user to users: {email}")
        else:
            logger.info(f"Microsoft user already exists: {email}")