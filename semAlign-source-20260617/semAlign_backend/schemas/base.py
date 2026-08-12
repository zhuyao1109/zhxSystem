"""基础响应模型"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    标准 API 响应格式
    
    核心字段：
    - code: 响应码（200=成功，其他=失败）
    - message: 响应消息
    - data: 响应数据（泛型）
    """
    
    code: int = Field(200, description="响应码（200=成功，其他=失败）")
    message: str = Field("success", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": {},
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应格式
    
    核心字段：
    - data: 当前页数据列表
    - total: 总记录数
    - page: 当前页码（从 1 开始）
    - size: 每页记录数
    - pages: 总页数
    """
    
    data: List[T] = Field(..., description="当前页数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码（从 1 开始）")
    size: int = Field(..., description="每页记录数")
    pages: int = Field(..., description="总页数（total / size 向上取整）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": [],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10,
            }
        }


class MessageResponse(BaseModel):
    """
    简单消息响应 - 用于无数据返回的操作
    
    典型场景：删除、更新、批量操作等
    """
    
    message: str = Field(..., description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "操作成功"
            }
        }