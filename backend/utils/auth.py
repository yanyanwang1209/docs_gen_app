"""JWT 认证工具"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt
from backend.config import settings

# 算法
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """对密码进行哈希"""
    salt = secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, h = password_hash.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: str, username: str, is_admin: bool = False) -> str:
    """创建 JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "is_admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解析 JWT token，返回 payload 或 None"""
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None