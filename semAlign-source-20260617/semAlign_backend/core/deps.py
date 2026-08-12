"""依赖注入函数 - 处理用户认证和权限控制"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .security import security, verify_token
from models.user import User


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    获取当前认证用户 - 从 JWT Token 中解析用户信息
    
    业务逻辑：
    1. 从请求头中提取 Bearer Token
    2. 验证 Token 签名和过期时间
    3. 从 Token 中提取用户 ID
    4. 从数据库查询用户信息
    5. 返回用户对象或抛出认证异常
    
    使用场景：
        - 需要用户登录的接口
        - 获取当前用户信息
        
    使用示例：
        @router.get("/profile")
        def get_profile(current_user: User = Depends(get_current_user)):
            return {"username": current_user.username}
    
    Args:
        credentials: HTTP Bearer 认证凭证
        db: 数据库会话
    
    Returns:
        User: 当前认证用户对象
    
    Raises:
        HTTPException(401): Token 无效、过期或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 验证 Token 并提取用户 ID
    user_id = verify_token(credentials)
    if user_id is None:
        raise credentials_exception
    
    # 从数据库查询用户
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户 - 检查用户账户是否激活
    
    业务逻辑：
    1. 验证用户是否已登录（依赖 get_current_user）
    2. 检查用户账户状态（is_active 字段）
    3. 如果账户未激活，抛出 403 禁止访问异常
    
    使用场景：
        - 需要活跃用户的接口
        - 防止被禁用的用户访问系统
        
    使用示例：
        @router.post("/orders")
        def create_order(current_user: User = Depends(get_current_active_user)):
            # 只有活跃用户才能创建订单
            pass
    
    Args:
        current_user: 当前认证用户（通过 get_current_user 获取）
    
    Returns:
        User: 当前活跃用户对象
    
    Raises:
        HTTPException(403): 用户账户已被禁用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用，请联系管理员"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    获取当前管理员用户 - 检查用户是否具有管理员权限
    
    业务逻辑：
    1. 验证用户是否已登录（依赖 get_current_active_user）
    2. 检查用户角色是否为 admin
    3. 如果不是管理员，抛出 403 权限不足异常
    
    使用场景：
        - 需要管理员权限的接口
        - 标准管理、用户管理等敏感操作
        
    使用示例：
        @router.delete("/users/{user_id}")
        def delete_user(current_user: User = Depends(get_current_admin_user)):
            # 只有管理员才能删除用户
            pass
    
    Args:
        current_user: 当前活跃用户（通过 get_current_active_user 获取）
    
    Returns:
        User: 当前管理员用户对象
    
    Raises:
        HTTPException(403): 用户权限不足
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user