"""导入历史模型 - 记录标准导入操作"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseModel


class ImportHistory(BaseModel):
    """
    导入历史记录模型

    记录每次标准导入操作的详细信息：
    - 导入时间、操作用户
    - 导入方式（文件上传/批量导入）
    - 导入结果（成功/失败数量）
    - 文件信息

    表名: import_history，主键: id
    """

    __tablename__ = "import_history"

    # 导入类型
    import_type = Column(
        String(20),
        nullable=False,
        comment="导入类型（upload/batch）"
    )

    # 文件名
    filename = Column(
        String(255),
        nullable=True,
        comment="原始文件名"
    )

    # 保存的文件名
    saved_filename = Column(
        String(255),
        nullable=True,
        comment="服务器保存的文件名"
    )

    # 导入状态
    status = Column(
        String(20),
        nullable=False,
        default="success",
        comment="导入状态（success/failed/partial）"
    )

    # 成功数量
    success_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="成功导入的标准数量"
    )

    # 失败数量
    failed_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="导入失败的标准数量"
    )

    # 错误信息
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息（如果有）"
    )

    # 操作用户ID
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="操作用户ID"
    )

    # 关联用户
    user = relationship("User", backref="import_histories")

    def __repr__(self) -> str:
        return f"<ImportHistory(id={self.id}, type='{self.import_type}', status='{self.status}', success={self.success_count}, failed={self.failed_count})>"
