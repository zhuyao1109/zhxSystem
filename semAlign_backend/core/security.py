"""安全认证模块 - 处理密码加密、JWT Token 生成和验证"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

# bcrypt密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token提取
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与加密密码匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """使用bcrypt算法加密明文密码"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建JWT访问令牌，包含用户信息和过期时间"""
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    # 使用配置的密钥和算法进行签名
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码并验证JWT令牌，返回payload或None"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        # Token 无效或已过期
        return None


def verify_token(credentials: HTTPAuthorizationCredentials) -> Optional[str]:
    """验证Bearer Token并提取用户ID"""
    if not credentials:
        return None
    
    try:
        payload = decode_access_token(credentials.credentials)
        if payload is None:
            return None
        user_id: str = payload.get("sub")
        return user_id
    except Exception:
        return None