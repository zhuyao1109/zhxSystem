"""应用主入口 - FastAPI 应用配置和启动。

职责：
    注册全部业务路由、CORS、生命周期钩子（建表/初始化）；
    暴露 /health 健康检查与 /docs OpenAPI 文档。

路由模块：
    auth, standards, import, search, alignment, comparison, workbench 等。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from core.config import settings
from core.database import engine, Base
import models  # noqa: F401  # 显式导入模型，确保 startup 时可创建全部表
from routers import (
    auth,
    workbench,
    standards,
    term_conflicts,
    conflict_dialogues,
    vector_store,
    standard_import,
    search,
    alignment,
    comparison,
    report_export,
    rules,
    user,
    statistics,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    业务逻辑：
        - 启动时：创建数据库表
        - 关闭时：清理资源
    
    使用场景：
        - 数据库初始化
        - 连接池管理
        - 缓存预热
    """
    # 启动时执行
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时执行（清理资源）


# ==================== FastAPI 应用配置 ====================
app = FastAPI(
    title="SemAlign API",
    version="1.0.0",
    description="中航信标准管理系统 API",
    docs_url="/docs",  # 本地调试 Swagger UI；不需要时改回 None
    redoc_url="/redoc",  # ReDoc；不需要时改回 None
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ==================== CORS 跨域配置 ====================
# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,    # 允许的源地址
    allow_credentials=True,                  # 允许携带凭证
    allow_methods=["*"],                     # 允许所有 HTTP 方法
    allow_headers=["*"],                     # 允许所有请求头
)

# ==================== 路由注册 ====================
# 注册各业务模块的路由
app.include_router(auth.router, prefix="/api")
app.include_router(workbench.router, prefix="/api")
app.include_router(standards.router, prefix="/api")
app.include_router(term_conflicts.router, prefix="/api")
app.include_router(conflict_dialogues.router, prefix="/api")
app.include_router(vector_store.router, prefix="/api")
app.include_router(standard_import.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(alignment.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(comparison.router, prefix="/api")
app.include_router(report_export.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(user.router, prefix="/api")


# ==================== 系统接口 ====================

@app.get("/doc", include_in_schema=False)
async def redirect_doc_to_docs() -> RedirectResponse:
    """常见笔误 /doc → 正式路径为 /docs（带 s）。"""
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/", tags=["系统"])
async def root():
    """
    根路径接口
    
    业务逻辑：
        - 返回 API 基本信息
    
    返回数据：
        - message: 欢迎消息
        - version: API 版本
    """
    return {
        "message": "SemAlign API is running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查接口
    
    业务逻辑：
        - 用于监控和负载均衡器检查
        - 返回健康状态
    
    返回数据：
        - status: 健康状态
    """
    return {"status": "healthy"}


# ==================== 应用启动 ====================
if __name__ == "__main__":
    import uvicorn
    # 开发环境启动（支持热重载）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug  # 调试模式启用热重载
    )
