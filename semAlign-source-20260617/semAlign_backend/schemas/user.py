"""用户相关模型 - 定义用户 API 的请求和响应格式"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from .base import APIResponse


class UserBase(BaseModel):
    """用户基础模型，定义公共字段"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50 字符）")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    role: str = Field("user", description="用户角色（user/admin）")


class UserCreate(UserBase):
    """用户创建模型，包含密码字段"""
    
    password: str = Field(..., min_length=6, description="密码（至少 6 字符）")


class UserUpdate(BaseModel):
    """用户更新模型，可选字段"""

    email: Optional[EmailStr] = None
    avatar: Optional[str] = None


class AdminUserUpdate(BaseModel):
    """管理员更新用户模型"""

    role: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""

    old_password: str = Field(..., min_length=1, description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少 6 字符）")


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求模型"""

    username_or_email: str = Field(..., min_length=1, description="用户名或邮箱")
    new_password: str = Field(..., min_length=6, description="新密码（至少 6 字符）")


class UserResponse(UserBase):
    """用户响应模型，不包含敏感信息"""
    
    id: int
    is_active: bool
    avatar: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登录请求（与认证路由一致）"""

    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录响应（OAuth2 风格 access_token + 用户信息）"""

    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    user: UserResponse





class UserLoginResponse(BaseModel):
    """登录响应模型，包含令牌和用户信息"""
    
    token: str = Field(..., description="JWT 访问令牌")
    user: UserResponse = Field(..., description="用户信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "role": "admin",
                    "is_active": True,
                },
            }
        }


