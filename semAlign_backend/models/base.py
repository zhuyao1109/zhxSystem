"""数据库模型基类 - 提供公共字段和方法"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from core.database import Base


class TimestampMixin:
    """
    时间戳混入类 - 提供标准时间戳字段
    
    id: 主键
    created_at: 创建时间
    updated_at: 更新时间
    """
    
    id = Column(Integer, primary_key=True, index=True, comment="主键 ID")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )


class BaseModel(Base, TimestampMixin):
    """
    基础模型类 - 所有数据库模型的基类
    
    自动包含：
    - id: 主键
    - created_at: 创建时间
    - updated_at: 更新时间
    - to_dict(): 序列化方法
    
    抽象基类，所有业务模型应继承此类
    """
    
    __abstract__ = True
    
    def to_dict(self):
        """模型对象转字典，用于JSON序列化"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}