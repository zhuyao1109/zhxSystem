"""对齐相关模型 - 定义标准对齐 API 的请求和响应格式"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class AlignmentTaskCreate(BaseModel):
    """
    对齐任务创建模型
    
    text: 待对齐文本内容
    options: 对齐选项配置
    """
    
    text: str = Field(..., min_length=1, description="待对齐的文本内容")
    options: dict = Field(default_factory=dict, description="对齐选项（可选）")


class AlignmentTaskResponse(BaseModel):
    """
    对齐任务响应模型
    
    核心字段：
    - id: 任务 ID
    - user_id: 创建用户 ID
    - input_text: 输入文本
    - status: 任务状态
    - result_json: 对齐结果
    - options: 对齐选项
    - created_at: 创建时间
    - completed_at: 完成时间戳
    """
    
    id: int
    user_id: int
    input_text: str
    status: str
    result_json: Optional[dict] = None
    options: Optional[dict] = None
    review_status: str = "draft"
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[int] = None
    
    class Config:
        from_attributes = True  # 允许从ORM模型转换


class AlignmentTaskListResponse(BaseModel):
    """
    对齐任务列表响应模型（分页）
    
    data: 任务列表
    total: 总任务数  
    page: 当前页码
    size: 每页数量
    """
    
    data: List[AlignmentTaskResponse] = Field(default_factory=list, description="任务列表")
    total: int = Field(..., description="总任务数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")


class ConflictItem(BaseModel):
    """
    冲突项模型
    
    id: 冲突ID
    title: 冲突标题  
    severity: 严重程度
    standard1: 标准1信息
    standard2: 标准2信息
    """
    
    id: str = Field(..., description="冲突 ID")
    title: str = Field(..., description="冲突标题")
    severity: str = Field(..., description="严重程度（low/medium/high）")
    standard1: dict = Field(..., description="标准 1 信息")
    standard2: dict = Field(..., description="标准 2 信息")


class AlignmentReviewRequest(BaseModel):
    """对齐审核请求"""

    action: str = Field(..., description="审核动作：submit/approve/reject/publish")
    notes: Optional[str] = Field(None, description="审核意见")


class ComparisonResult(BaseModel):
    """
    比对结果模型
    
    task_id: 任务ID
    conflicts: 冲突列表
    solutions: 解决方案列表  
    stats: 统计信息
    """
    
    task_id: str = Field(..., description="任务 ID")
    conflicts: List[ConflictItem] = Field(default_factory=list, description="冲突列表")
    solutions: List[dict] = Field(default_factory=list, description="解决方案列表")
    stats: dict = Field(default_factory=dict, description="统计信息")