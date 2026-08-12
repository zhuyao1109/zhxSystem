"""对齐任务模型 - 管理标准语义对齐任务"""

from enum import Enum
from sqlalchemy import Column, Text, JSON, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship

from .base import BaseModel


class AlignmentStatus(str, Enum):
    """
    对齐任务状态枚举
    
    状态流转：PENDING → PROCESSING → COMPLETED/FAILED
    """
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class AlignmentTask(BaseModel):
    """
    对齐任务模型 - 管理标准语义对齐任务
    
    核心字段：
    - user_id: 创建用户
    - input_text: 待对齐内容  
    - status: 任务状态
    - result_json: 对齐结果
    - options: 对齐配置
    
    表名: alignment_tasks，外键: user_id → users.id
    """
    
    __tablename__ = "alignment_tasks"
    
    # ==================== 关联信息 ====================
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="创建用户 ID"
    )
    
    # ==================== 任务内容 ====================
    input_text = Column(
        Text,
        nullable=False,
        comment="输入文本（待对齐的标准内容）"
    )
    
    # ==================== 任务状态 ====================
    status = Column(
        String(20),
        default=AlignmentStatus.PENDING.value,
        nullable=False,
        comment="任务状态（pending/processing/completed/failed）"
    )
    
    # ==================== 结果数据 ====================
    result_json = Column(
        JSON,
        nullable=True,
        comment="对齐结果（JSON 格式，包含冲突、建议等）"
    )
    options = Column(
        JSON,
        nullable=True,
        comment="对齐选项（JSON 格式，自定义配置）"
    )
    
    # ==================== 审核发布状态 ====================
    review_status = Column(
        String(20),
        default="draft",
        nullable=False,
        comment="审核状态（draft/submitted/approved/rejected/published）"
    )
    review_notes = Column(
        Text,
        nullable=True,
        comment="审核意见"
    )
    reviewed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="审核人 ID"
    )
    reviewed_at = Column(
        DateTime,
        nullable=True,
        comment="审核时间"
    )
    published_at = Column(
        DateTime,
        nullable=True,
        comment="发布时间"
    )

    # ==================== 时间戳 ====================
    completed_at = Column(
        Integer,
        nullable=True,
        comment="完成时间（Unix 时间戳）"
    )
    
    # ==================== 关系定义 ====================
    user = relationship("User", foreign_keys=[user_id], backref="alignment_tasks")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    def __repr__(self):
        """模型字符串表示"""
        return f"<AlignmentTask(id={self.id}, status='{self.status}', user_id={self.user_id})>"