"""比对结果反馈与修改意见模型。"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from .base import BaseModel


class ComparisonFeedback(BaseModel):
    """冲突反馈（赞成/反对）记录。"""

    __tablename__ = "comparison_feedbacks"

    task_id = Column(
        Integer,
        ForeignKey("alignment_tasks.id"),
        nullable=False,
        index=True,
        comment="任务ID",
    )
    conflict_id = Column(
        String(128),
        nullable=False,
        index=True,
        comment="冲突ID",
    )
    feedback_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="反馈类型（approve/reject）",
    )
    comment = Column(
        Text,
        nullable=True,
        comment="反馈备注",
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="提交用户ID",
    )
    user_name = Column(
        String(100),
        nullable=False,
        comment="提交用户名",
    )


class ComparisonModification(BaseModel):
    """对齐结果修改意见记录。"""

    __tablename__ = "comparison_modifications"

    task_id = Column(
        Integer,
        ForeignKey("alignment_tasks.id"),
        nullable=False,
        index=True,
        comment="任务ID",
    )
    modification_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="修改类型（suggestion/question/issue 等）",
    )
    content = Column(
        Text,
        nullable=False,
        comment="修改意见内容",
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="提交用户ID",
    )
    user_name = Column(
        String(100),
        nullable=False,
        comment="提交用户名",
    )
