"""应用配置管理 - 使用 Pydantic Settings 管理所有配置项"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类
    
    配置项说明：
    - 应用基础信息：名称、版本、环境
    - 服务器配置：主机地址、端口
    - 数据库配置：数据库连接 URL
    - 安全配置：JWT 密钥、算法、过期时间
    - CORS 配置：允许的跨域来源
    - 文件上传配置：上传目录、大小限制、允许的文件类型
    - 日志配置：日志级别、格式
    """

    # ==================== 应用基础配置 ====================
    app_name: str = "SemAlign API"
    app_version: str = "1.0.0"
    app_env: str = "development"  # 开发环境 / 生产环境
    debug: bool = True  # 是否开启调试模式（生产环境必须为 False）

    # ==================== 服务器配置 ====================
    host: str = "0.0.0.0"  # 监听地址
    port: int = 8000  # 监听端口

    # ==================== 数据库配置 ====================
    database_url: str = "sqlite:///./data/semalign.db"
    # 生产环境建议使用 PostgreSQL: postgresql://user:password@localhost:5432/semalign

    # ==================== 安全配置 ====================
    # JWT 认证相关配置
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        min_length=32,
        description="JWT 密钥（生产环境必须从环境变量读取）"
    )
    algorithm: str = "HS256"  # JWT 签名算法
    access_token_expire_minutes: int = 30  # 访问令牌有效期（分钟）

    # ==================== CORS 跨域配置 ====================
    # 允许的前端访问地址（根据实际前端部署地址修改）
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ==================== 文件上传配置 ====================
    upload_dir: str = "./data/uploads"  # 文件上传目录
    text_output_dir: str = "./data/texts"  # 抽取后的纯文本目录
    image_output_dir: str = "./data/images"  # PDF 图片抽取目录
    max_upload_size: int = 20971520  # 最大上传大小（20MB）
    allowed_extensions: List[str] = [".xlsx", ".xls", ".pdf"]  # 允许的文件类型

    # ==================== 向量检索配置 ====================
    vector_store_enabled: bool = True
    chroma_db_dir: str = "./data/chroma_db"
    bm25_index_path: str = "./data/bm25_chunks.pkl"
    embedding_model_dir: str = "./models/gte-multilingual-base"
    chroma_collection_name: str = "documents"
    vector_chunk_size: int = 400
    vector_chunk_overlap: int = 50
    vector_batch_size: int = 50
    bm25_weight: float = 0.3
    semantic_weight: float = 0.7

    # ==================== 搜索增强（可选 RAG） ====================
    search_rag_enabled: bool = False
    search_rag_top_k: int = 5

    # ==================== LLM 网关配置 ====================
    fourz_api_key: Optional[str] = None
    fourz_api_base: Optional[str] = None
    fourz_api_model: str = "gpt-4o-mini"
    deepseek_api_key: Optional[str] = None
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_api_model: str = "deepseek-chat"

    # 对齐助手：llm=优先大模型 | vector_engine=向量+标准库检索 | auto=有 Key 用 llm 否则 vector_engine
    alignment_chat_mode: str = "auto"

    # ==================== OCR 配置 ====================
    ocr_dpi: int = 300
    ocr_min_image_size: int = 100
    ocr_min_stddev: float = 10.0

    # ==================== 日志配置 ====================
    log_level: str = "INFO"  # 日志级别：DEBUG / INFO / WARNING / ERROR
    log_format: str = "json"  # 日志格式：json / text

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """解析 CORS 来源（支持逗号分隔的字符串）"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


# 全局配置实例（单例模式）
settings = Settings()
