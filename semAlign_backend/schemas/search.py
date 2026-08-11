"""搜索相关模型"""

from typing import List
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """
    搜索结果模型
    
    包含标准信息和相关度评分
    """
    
    id: int
    standard_no: str
    name: str
    version: str
    status: str
    category: str
    department: str | None = None
    relevance_score: float = Field(0.0, ge=0.0, le=1.0, description="相关度评分（0-1）")
    source_file: str | None = Field(None, description="来源文件")
    match_type: str | None = Field(None, description="命中类型（metadata/vector/hybrid）")
    match_excerpt: str | None = Field(None, description="命中文本片段")


class SearchSuggestion(BaseModel):
    """
    搜索建议模型 - 用于搜索框自动补全
    
    包含建议类型、文本和匹配数量
    """
    
    type: str = Field(..., description="建议类型（标准号/名称/分类）")
    text: str = Field(..., description="建议文本")
    count: int = Field(0, description="匹配数量")


class SearchResponse(BaseModel):
    """
    搜索响应模型
    
    核心字段：
    - results: 搜索结果列表
    - suggestions: 搜索建议列表
    - total: 总结果数
    """
    
    results: List[SearchResult] = Field(default_factory=list, description="搜索结果列表")
    answer: str = Field("", description="可选：RAG 大模型回答（开关启用时返回）")
    sources: List[str] = Field(default_factory=list, description="可选：RAG 引用来源（开关启用时返回）")
    suggestions: List[SearchSuggestion] = Field(default_factory=list, description="搜索建议列表")
    total: int = Field(0, description="总结果数")
