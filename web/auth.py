import jwt
import datetime
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyCookie
from pydantic import BaseModel
from typing import Optional

# Security Configuration
SECRET_KEY = "super-secret-ai-security-key-do-not-use-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

cookie_sec = APIKeyCookie(name="session_token", auto_error=False)

class LoginData(BaseModel):
    username: str
    password: str

# Hardcoded single user for MVP
VALID_USERNAME = "admin"
VALID_PASSWORD = "securepassword"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_optional(token: str = Security(cookie_sec)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

def get_current_user(token: str = Security(cookie_sec)):
    username = get_current_user_optional(token)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username
