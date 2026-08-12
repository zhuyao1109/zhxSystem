"""标准模型 - 管理标准元数据和状态"""

from sqlalchemy import Column, String, Text, Boolean

from .base import BaseModel


class Standard(BaseModel):
    """
    标准模型 - 管理标准元数据
    
    核心字段：
    - standard_no: 标准号，唯一标识如 "GB/T 12345-2020"
    - name: 标准名称
    - version: 版本号如 "V1.0"
    - status: 状态（有效/失效/修订中）
    - category: 分类（基础通用/业务标准等）
    - department: 负责部门
    - description: 描述说明
    - is_active: 激活状态
    
    扩展字段：
    - conflict_status: 冲突状态
    - rule_violations: 规则违反记录
    - source_file: 来源文件
    
    表名: standards，主键: id
    """
    
    __tablename__ = "standards"
    
    # ==================== 基础信息 ====================
    standard_no = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="标准号（唯一标识，如 GB/T 12345-2020）"
    )
    name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="标准名称"
    )
    version = Column(
        String(20),
        nullable=False,
        comment="版本号（如 V1.0、V2.1）"
    )
    status = Column(
        String(20),
        default="有效",
        nullable=False,
        comment="标准状态（有效/失效/修订中/草稿）"
    )
    category = Column(
        String(50),
        default="未分类",
        nullable=False,
        comment="标准分类（基础通用/业务标准/技术标准等）"
    )
    department = Column(
        String(50),
        nullable=True,
        comment="负责部门"
    )
    description = Column(
        Text,
        nullable=True,
        comment="标准描述和说明"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活（True=正常使用，False=已删除）"
    )
    
    # ==================== 扩展字段（语义对齐相关） ====================
    conflict_status = Column(
        String(20),
        default="无冲突",
        nullable=True,
        comment="冲突状态（无冲突/有冲突/待处理）"
    )
    rule_violations = Column(
        Text,
        nullable=True,
        comment="规则违反记录（JSON 格式存储详细违反信息）"
    )
    source_file = Column(
        String(200),
        nullable=True,
        comment="来源文件（导入时的原始文件名）"
    )
    
    def __repr__(self):
        """模型字符串表示"""
        return f"<Standard(id={self.id}, standard_no='{self.standard_no}', name='{self.name}')>"