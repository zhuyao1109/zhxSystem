"""标准库接口测试。"""

from __future__ import annotations


class TestStandardsApi:
    def test_list_standards_empty(self, client) -> None:
        response = client.get("/api/standards")
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert body["data"]["total"] == 0

    def test_list_standards_with_data(self, client, sample_standard) -> None:
        response = client.get("/api/standards", params={"search": "信息安全"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["total"] >= 1
        assert body["data"]["data"][0]["standard_no"] == "GB/T 90001-2020"

    def test_get_standard_detail(self, client, sample_standard) -> None:
        response = client.get(f"/api/standards/{sample_standard.id}")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "信息安全管理规范"

    def test_get_standard_not_found(self, client) -> None:
        response = client.get("/api/standards/99999")
        assert response.status_code == 404

    def test_filter_options(self, client, sample_standard) -> None:
        response = client.get("/api/standards/filter-options")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "安全管理" in data.get("categories", [])
