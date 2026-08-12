"""数据库配置和会话管理 - 处理数据库连接、会话管理和表初始化"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from .config import settings

# ==================== 数据库引擎配置 ====================
# 创建数据库引擎（连接池）
engine = create_engine(
    settings.database_url,
    # SQLite 特殊配置：允许多线程访问
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    # 启用连接池健康检查（防止使用失效的连接）
    pool_pre_ping=True,
    # 调试模式：打印所有 SQL 语句（生产环境关闭）
    echo=settings.debug,
)

# ==================== 数据库会话工厂 ====================
# 创建会话工厂，用于生成数据库会话
# autocommit=False: 不自动提交事务
# autoflush=False: 不自动刷新变更（需要手动提交）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== 模型基类 ====================
# 所有数据库模型都继承此基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    依赖注入函数 - 获取数据库会话
    
    业务逻辑：
    - 每个请求都会获得一个独立的数据库会话
    - 会话在请求开始时创建
    - 会话在请求结束时自动关闭
    - 使用 try-finally 确保会话总是被正确关闭
    
    使用方式：
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    
    Yields:
        Session: 数据库会话对象
    
    注意事项：
        - 不要手动关闭会话，FastAPI 会自动处理
        - 每个请求使用独立的会话，避免并发问题
        - 修改数据后必须调用 db.commit() 提交事务
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库 - 创建所有表
    
    业务逻辑：
    - 扫描所有继承自 Base 的模型类
    - 自动创建对应的数据库表
    - 如果表已存在则跳过
    - 建议在应用启动时调用
    
    使用方式：
        # main.py
        @app.on_event("startup")
        async def startup_event():
            init_db()
    
    注意事项：
        - 生产环境建议使用 Alembic 进行数据库迁移
        - init_db 适用于开发环境和快速原型
        - 不会删除或修改已有的表结构
    """
    Base.metadata.create_all(bind=engine)