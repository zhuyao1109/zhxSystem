"""冲突问答及与术语冲突映射模型。"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class ConflictDialogue(BaseModel):
    """冲突问答明细表。"""

    __tablename__ = "conflict_dialogues"

    dialogue_id = Column(String(64), nullable=False, unique=True, index=True, comment="问答唯一ID")
    original_conflict_id = Column(String(64), nullable=False, index=True, comment="原始冲突ID")
    question = Column(Text, nullable=False, comment="问题文本")
    answer = Column(Text, nullable=False, comment="答案文本")
    answer_clean = Column(Text, nullable=True, comment="清洗后的答案")
    source_document = Column(Text, nullable=False, comment="来源文档")
    source_paragraph = Column(Text, nullable=False, comment="来源段落")
    dialogue_type = Column(String(100), nullable=False, default="unknown", comment="问答类型")
    style = Column(String(100), nullable=False, default="unknown", comment="问答风格")
    cluster = Column(String(100), nullable=False, default="unknown", index=True, comment="聚类标识")
    conflict_type = Column(String(100), nullable=False, index=True, comment="冲突类型")
    source_file = Column(String(255), nullable=False, comment="导入文件名")

    mappings = relationship("ConflictDialogueMapping", back_populates="dialogue")


class ConflictDialogueMapping(BaseModel):
    """问答冲突与术语冲突映射表。"""

    __tablename__ = "conflict_dialogue_mappings"

    dialogue_id = Column(
        Integer,
        ForeignKey("conflict_dialogues.id"),
        nullable=False,
        index=True,
        comment="问答记录ID",
    )
    original_conflict_id = Column(String(64), nullable=False, index=True, comment="原始冲突ID")
    term_conflict_id = Column(
        Integer,
        ForeignKey("term_conflicts.id"),
        nullable=False,
        index=True,
        comment="术语冲突ID",
    )
    matched_by = Column(String(100), nullable=False, default="rule_based", comment="映射方法")
    confidence = Column(Float, nullable=False, default=0.0, comment="映射置信度")
    note = Column(Text, nullable=True, comment="映射说明")

    dialogue = relationship("ConflictDialogue", back_populates="mappings")
    term_conflict = relationship("TermConflict")

    __table_args__ = (
        UniqueConstraint("dialogue_id", "term_conflict_id", name="uq_dialogue_term_conflict"),
    )
