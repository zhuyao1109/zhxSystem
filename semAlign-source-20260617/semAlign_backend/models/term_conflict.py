"""术语冲突相关模型 - 术语、冲突事实、导入批次"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class ImportBatch(BaseModel):
    """导入批次记录"""

    __tablename__ = "import_batches"

    file_name = Column(String(255), nullable=False, comment="导入文件名")
    file_hash = Column(String(64), nullable=False, index=True, comment="文件 SHA256")
    source_type = Column(
        String(50),
        nullable=False,
        default="terminology_conflict_csv",
        comment="来源类型",
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="批次状态（pending/processing/completed/failed）",
    )
    total_rows = Column(Integer, nullable=False, default=0, comment="总行数")
    success_rows = Column(Integer, nullable=False, default=0, comment="成功行数")
    failed_rows = Column(Integer, nullable=False, default=0, comment="失败行数")
    error_log = Column(Text, nullable=True, comment="错误摘要")

    conflicts = relationship("TermConflict", back_populates="batch")


class Term(BaseModel):
    """术语维表"""

    __tablename__ = "terms"

    name = Column(String(255), nullable=False, comment="术语原文")
    name_norm = Column(String(255), nullable=False, unique=True, index=True, comment="术语规范名")

    conflicts = relationship("TermConflict", back_populates="term")


class TermConflict(BaseModel):
    """术语冲突事实表"""

    __tablename__ = "term_conflicts"

    term_id = Column(
        Integer,
        ForeignKey("terms.id"),
        nullable=False,
        index=True,
        comment="术语 ID",
    )
    standard_no_1 = Column(String(100), nullable=False, index=True, comment="来源标准号1")
    standard_no_2 = Column(String(100), nullable=False, index=True, comment="来源标准号2")
    pair_key = Column(String(220), nullable=False, index=True, comment="标准对键（有序）")
    conflict_type = Column(String(50), nullable=False, index=True, comment="冲突类型")
    conflict_desc = Column(Text, nullable=False, comment="冲突描述")
    source_file = Column(String(255), nullable=False, comment="来源文件名")
    batch_id = Column(
        Integer,
        ForeignKey("import_batches.id"),
        nullable=True,
        index=True,
        comment="导入批次 ID",
    )

    term = relationship("Term", back_populates="conflicts")
    batch = relationship("ImportBatch", back_populates="conflicts")

    __table_args__ = (
        UniqueConstraint(
            "term_id",
            "pair_key",
            "conflict_type",
            "conflict_desc",
            name="uq_term_conflict_dedup",
        ),
    )
