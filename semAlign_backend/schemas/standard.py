"""标准相关模型 - 定义标准 API 的请求和响应格式"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .base import APIResponse, PaginatedResponse


class StandardBase(BaseModel):
    """标准基础模型，定义公共字段"""
    
    standard_no: str = Field(..., description="标准号（如 GB/T 12345-2020）")
    name: str = Field(..., description="标准名称")
    version: str = Field(..., description="版本号（如 V1.0、V2.1）")
    status: str = Field("有效", description="标准状态（有效/失效/修订中/草稿）")
    category: str = Field("未分类", description="标准分类（基础通用/业务标准/技术标准）")
    department: Optional[str] = Field(None, description="负责部门")
    description: Optional[str] = Field(None, description="标准描述")


class StandardCreate(StandardBase):
    """标准创建模型，继承基础字段"""
    pass


class StandardUpdate(BaseModel):
    """标准更新模型，可选字段更新"""
    
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StandardResponse(StandardBase):
    """标准响应模型，包含详细信息"""
    
    id: int
    is_active: bool
    conflict_status: Optional[str] = None
    rule_violations: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True




class StandardListResponse(PaginatedResponse[StandardResponse]):
    """标准列表响应模型（分页）"""
    pass
