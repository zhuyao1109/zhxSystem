"""配置与比对路由测试。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.config import Settings
from core.database import get_db
from core.deps import get_current_user
from models.alignment_task import AlignmentTask
from routers import comparison
from tests.auth_overrides import override_get_current_user


@asynccontextmanager
async def _empty_lifespan(_: FastAPI):
    yield


def _make_comparison_app():
    app = FastAPI(lifespan=_empty_lifespan)
    app.include_router(comparison.router, prefix="/api")
    return app


def _sample_result_json() -> dict:
    return {
        "standard_group1": "标准A",
        "standard_group2": "标准B",
        "comparison_time": "2026-06-05T10:00:00",
        "stats": {"conflict_rate": 0.2, "match_rate": 0.7, "pending_rate": 0.1},
        "clusters": [{"id": "cluster-1", "label": "语义簇1"}],
        "conflicts": [{"id": "conflict-1", "title": "冲突1"}],
        "solutions": [{"id": "solution-1", "title": "方案1"}],
        "report_text": "检测报告",
        "meta": {"pipeline": {"version": "v1", "layers": ["l1", "l2"]}},
    }


class TestSettings:
    def test_parse_cors_origins_string(self):
        result = Settings.parse_cors_origins("http://a.com, http://b.com")
        assert result == ["http://a.com", "http://b.com"]

    def test_parse_cors_origins_list(self):
        origins = ["http://localhost:8080"]
        assert Settings.parse_cors_origins(origins) == origins


class TestComparisonApi:
    def test_comparison_endpoints(self, memory_session, test_user):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="比对测试",
            status="completed",
            result_json=_sample_result_json(),
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                base = f"/api/comparison"
                tid = str(task.id)
                assert client.get(f"{base}/task/{tid}").status_code == 200
                assert client.get(f"{base}/stats/{tid}").status_code == 200
                assert client.get(f"{base}/clusters/{tid}").status_code == 200
                assert client.get(f"{base}/conflicts/{tid}").status_code == 200
                assert client.get(f"{base}/solutions/{tid}").status_code == 200
                assert client.get(f"{base}/report/{tid}").status_code == 200
                assert client.get(f"{base}/feedback/conflict-1").status_code == 200
                feedback = client.post(
                    f"{base}/feedback",
                    json={
                        "task_id": task.id,
                        "conflict_id": "conflict-1",
                        "action": "approve",
                    },
                )
                assert feedback.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_comparison_invalid_task_id(self, memory_session, test_user):
        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                assert client.get("/api/comparison/task/t1").status_code == 400
                assert client.get("/api/comparison/task/0").status_code == 400
        finally:
            app.dependency_overrides.clear()

    def test_comparison_task_not_found(self, memory_session, test_user):
        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                assert client.get("/api/comparison/task/999").status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_comparison_task_forbidden(self, memory_session, test_user):
        other_user_id = test_user.id + 100
        task = AlignmentTask(
            user_id=other_user_id,
            input_text="他人任务",
            status="completed",
            review_status="draft",
            result_json=_sample_result_json(),
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                assert client.get(f"/api/comparison/task/{task.id}").status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_comparison_task_not_completed(self, memory_session, test_user):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="未完成",
            status="pending",
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                assert client.get(f"/api/comparison/stats/{task.id}").status_code == 409
        finally:
            app.dependency_overrides.clear()

    def test_comparison_feedback_validation(self, memory_session, test_user):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="反馈校验",
            status="completed",
            result_json=_sample_result_json(),
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                missing_task = client.post(
                    "/api/comparison/feedback",
                    json={"conflict_id": "c1", "action": "approve"},
                )
                assert missing_task.status_code == 400

                missing_conflict = client.post(
                    "/api/comparison/feedback",
                    json={"task_id": task.id, "action": "approve"},
                )
                assert missing_conflict.status_code == 400

                bad_type = client.post(
                    "/api/comparison/feedback",
                    json={"task_id": task.id, "conflict_id": "c1", "action": "maybe"},
                )
                assert bad_type.status_code == 400
        finally:
            app.dependency_overrides.clear()

    def test_comparison_modification_flow(self, memory_session, test_user):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="修改意见测试",
            status="completed",
            result_json=_sample_result_json(),
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        app = _make_comparison_app()

        def override_get_db():
            yield memory_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user(test_user)
        try:
            with TestClient(app) as client:
                missing = client.post(
                    "/api/comparison/feedback/modification",
                    json={"task_id": task.id, "type": "note"},
                )
                assert missing.status_code == 400

                submit = client.post(
                    "/api/comparison/feedback/modification",
                    json={"task_id": task.id, "type": "note", "content": "建议修订"},
                )
                assert submit.status_code == 200

                listed = client.get(f"/api/comparison/feedback/modification/{task.id}")
                assert listed.status_code == 200
                assert len(listed.json()["data"]["modifications"]) == 1
        finally:
            app.dependency_overrides.clear()
