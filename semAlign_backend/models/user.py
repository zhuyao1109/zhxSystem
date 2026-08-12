"""用户模型 - 管理用户信息和权限"""

from enum import Enum
from sqlalchemy import Column, String, Boolean
from pydantic import EmailStr

from .base import BaseModel


class UserRole(str, Enum):
    """
    用户角色枚举
    
    USER: 普通用户 - 基础操作权限
    ADMIN: 管理员 - 完整系统权限
    """
    USER = "user"  # 普通用户
    ADMIN = "admin"  # 管理员


class User(BaseModel):
    """
    用户模型 - 用户认证和基础信息管理
    
    字段说明：
    - username: 登录用户名（唯一）
    - email: 邮箱地址（可选，唯一） 
    - password_hash: bcrypt加密密码
    - role: 用户角色（user/admin）
    - is_active: 账户状态
    - avatar: 头像URL（可选）
    
    表名: users，主键: id
    """
    
    __tablename__ = "users"
    
    # ==================== 认证信息 ====================
    username = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="用户名（登录凭证）"
    )
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        comment="邮箱地址"
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="密码哈希值（bcrypt 加密）"
    )
    
    # ==================== 权限和状态 ====================
    role = Column(
        String(20),
        default=UserRole.USER.value,
        nullable=False,
        comment="用户角色（user/admin）"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="账户状态（True=正常，False=禁用）"
    )
    
    # ==================== 个人资料 ====================
    avatar = Column(
        String(500),
        nullable=True,
        comment="头像 URL"
    )
    
    def __repr__(self):
        """
        模型字符串表示
        
        Returns:
            str: 用户信息的字符串表示
        """
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"