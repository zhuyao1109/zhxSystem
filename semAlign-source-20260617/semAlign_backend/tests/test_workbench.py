"""
工作台 API 测试：仅通过 HTTP 客户端请求 GET /api/workbench/dashboard。

登录与认证（本文件不调用登录接口）：
    真实环境需携带 JWT（Bearer），由 get_current_user 解析并查库。
    此处使用 FastAPI 的 dependency_overrides：将 get_current_user 替换为
    override_get_current_user(user)，请求时不再校验 Token，直接注入内存中的 User。
    这与「先 POST /auth/login 再带 access_token」是两条路径；覆盖依赖仅用于单测隔离。

查看接口返回的日志：pytest tests/test_workbench.py -v --log-cli-level=INFO
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from core.deps import get_current_user
from models.alignment_task import AlignmentTask  # noqa: F401
from models.standard import Standard
from models.user import User
from routers import workbench
from tests.auth_overrides import override_get_current_user

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _empty_lifespan(_: FastAPI):
    yield


def _make_test_app() -> FastAPI:
    application = FastAPI(title="SemAlign Test", lifespan=_empty_lifespan)
    application.include_router(workbench.router, prefix="/api")
    return application


_workbench_app = _make_test_app()


def _log_dashboard_response(response) -> None:
    """将接口原始状态码与 JSON 体写入日志。"""
    logger.info("GET /api/workbench/dashboard -> status=%s", response.status_code)
    try:
        body = response.json()
    except json.JSONDecodeError:
        logger.info("GET /api/workbench/dashboard -> text=%s", response.text)
    else:
        logger.info(
            "GET /api/workbench/dashboard -> body=\n%s",
            json.dumps(body, ensure_ascii=False, indent=2),
        )


class TestWorkbenchDashboard:
    """工作台仪表盘：仅包含对接口的 HTTP 请求与响应日志。"""

    @pytest.fixture
    def memory_session(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        user = User(
            username="workbench_tester",
            password_hash="dummy",
            role="user",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        yield session, user
        session.close()
        Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def client_authed(self, memory_session):
        db, user = memory_session

        def override_get_db():
            try:
                yield db
            finally:
                pass

        # 登录认证绕过：见模块顶注释；此处等价于「已登录的当前用户」注入。
        _workbench_app.dependency_overrides[get_db] = override_get_db
        _workbench_app.dependency_overrides[get_current_user] = override_get_current_user(user)
        try:
            with TestClient(_workbench_app) as client:
                yield client
        finally:
            _workbench_app.dependency_overrides.clear()

    def test_get_dashboard(self, client_authed) -> None:
        response = client_authed.get("/api/workbench/dashboard")
        _log_dashboard_response(response)
        assert response.status_code == 200

    def test_get_dashboard_after_insert_standard(self, memory_session, client_authed) -> None:
        db, _user = memory_session
        db.add(
            Standard(
                standard_no="GB/T 90001-2020",
                name="测试标准",
                version="V1",
                status="有效",
                category="基础通用",
                department="测试部",
                description="",
                is_active=True,
                conflict_status="无冲突",
            )
        )
        db.commit()

        response = client_authed.get("/api/workbench/dashboard")
        _log_dashboard_response(response)
        assert response.status_code == 200
