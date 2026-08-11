"""导入相关模型"""

from typing import List, Any
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """
    验证结果模型
    
    核心字段：
    - total_rows: 总行数
    - valid_rows: 有效行数
    - need_update: 需要更新的行数
    - duplicate_rows: 重复行数
    - data: 验证后的数据列表
    """
    
    total_rows: int = Field(..., description="总行数")
    valid_rows: int = Field(..., description="有效行数")
    need_update: int = Field(..., description="需要更新的行数")
    duplicate_rows: int = Field(..., description="重复行数")
    invalid_rows: int = Field(0, description="无效行数")
    data: List[dict] = Field(default_factory=list, description="验证后的数据列表")


class UploadResponse(BaseModel):
    """
    文件上传响应模型
    
    包含文件信息和验证结果
    """
    
    filename: str = Field(..., description="上传的文件名")
    saved_filename: str | None = Field(None, description="服务器保存后的文件名")
    status: str = Field(..., description="上传状态（success/failed）")
    validation: ValidationResult = Field(..., description="验证结果")
    message: str = Field(..., description="消息说明")


class ImportResponse(BaseModel):
    """
    导入响应模型
    
    核心字段：
    - imported_count: 成功导入的数量
    - failed_count: 导入失败的数量
    - errors: 错误信息列表
    """
    
    imported_count: int = Field(..., description="成功导入的数量")
    updated_count: int = Field(0, description="成功更新的数量")
    failed_count: int = Field(..., description="导入失败的数量")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")
