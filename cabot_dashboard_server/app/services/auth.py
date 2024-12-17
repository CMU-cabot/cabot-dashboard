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
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.oauth2_user_scheme = OAuth2PasswordBearer(tokenUrl="token")
        self.oauth2_client_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_user(self, username: str) -> Optional[UserInDB]:
        with open("users.json") as f:
            data = json.load(f)
            for user in data["users"]:
                if user["id"] == username:
                    return UserInDB(
                        username=user["id"],
                        hashed_password=user["password_hash"],
                        disabled=False
                    )
        return None

    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        user = self.get_user(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    async def get_current_user(self, token: str = None) -> User:
        if token is None:
            token = Depends(self.oauth2_user_scheme)
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception
        user = self.get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        return user

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

    async def validate_token(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
            return bool(payload.get("sub"))
        except JWTError:
            return False

    async def get_current_user_from_token(self, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            return self.get_user(username)
        except JWTError:
            return None