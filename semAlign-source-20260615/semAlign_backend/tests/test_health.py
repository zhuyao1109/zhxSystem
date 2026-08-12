"""系统健康检查。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


class TestHealth:
    def test_health_endpoint(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self) -> None:
        with TestClient(app) as client:
            response = client.get("/")
        assert response.status_code == 200
        assert "SemAlign API" in response.json()["message"]
