"""共享 pytest fixtures：内存 SQLite + 测试用 FastAPI 应用。"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from core.deps import get_current_user
from core.security import get_password_hash
from models.alignment_task import AlignmentTask  # noqa: F401
from models.standard import Standard
from models.user import User
from routers import alignment, auth, search, standards, workbench
from tests.auth_overrides import override_get_current_user


@asynccontextmanager
async def _empty_lifespan(_: FastAPI):
    yield


def make_test_app() -> FastAPI:
    application = FastAPI(title="SemAlign Test", lifespan=_empty_lifespan)
    application.include_router(auth.router, prefix="/api")
    application.include_router(standards.router, prefix="/api")
    application.include_router(search.router, prefix="/api")
    application.include_router(workbench.router, prefix="/api")
    application.include_router(alignment.router, prefix="/api")
    return application


_test_app = make_test_app()


@pytest.fixture
def memory_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(memory_session):
    user = User(
        username="tester",
        password_hash=get_password_hash("test1234"),
        email="tester@example.com",
        role="user",
        is_active=True,
    )
    memory_session.add(user)
    memory_session.commit()
    memory_session.refresh(user)
    return user


@pytest.fixture
def admin_user(memory_session):
    user = User(
        username="admin_tester",
        password_hash=get_password_hash("admin1234"),
        email="admin@example.com",
        role="admin",
        is_active=True,
    )
    memory_session.add(user)
    memory_session.commit()
    memory_session.refresh(user)
    return user


@pytest.fixture
def sample_standard(memory_session):
    standard = Standard(
        standard_no="GB/T 90001-2020",
        name="信息安全管理规范",
        version="V1.0",
        status="有效",
        category="安全管理",
        department="信息中心",
        description=(
            "1.1 组织应建立信息安全管理制度。"
            "1.2 组织应定期开展信息安全风险评估工作。"
        ),
        is_active=True,
        conflict_status="无冲突",
    )
    memory_session.add(standard)
    memory_session.commit()
    memory_session.refresh(standard)
    return standard


@pytest.fixture
def sample_standard_b(memory_session):
    standard = Standard(
        standard_no="ISO/IEC 27001:2022",
        name="信息安全管理体系",
        version="2022",
        status="有效",
        category="安全管理",
        department="信息中心",
        description=(
            "1.1 组织应建立信息安全管理体系并持续改进。"
            "1.2 组织应对信息资产进行分级分类并落实访问控制措施。"
        ),
        is_active=True,
        conflict_status="无冲突",
    )
    memory_session.add(standard)
    memory_session.commit()
    memory_session.refresh(standard)
    return standard


@pytest.fixture
def client(memory_session, test_user):
    def override_get_db():
        try:
            yield memory_session
        finally:
            pass

    _test_app.dependency_overrides[get_db] = override_get_db
    _test_app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
    try:
        with TestClient(_test_app) as test_client:
            yield test_client
    finally:
        _test_app.dependency_overrides.clear()


@pytest.fixture
def admin_client(memory_session, admin_user):
    def override_get_db():
        try:
            yield memory_session
        finally:
            pass

    _test_app.dependency_overrides[get_db] = override_get_db
    _test_app.dependency_overrides[get_current_user] = override_get_current_user(admin_user)
    try:
        with TestClient(_test_app) as test_client:
            yield test_client
    finally:
        _test_app.dependency_overrides.clear()
