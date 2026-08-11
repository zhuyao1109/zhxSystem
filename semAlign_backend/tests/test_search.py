"""智能检索接口测试。"""

from __future__ import annotations

from unittest.mock import patch


class TestSearchApi:
    def test_search_by_keyword(self, client, sample_standard) -> None:
        with (
            patch("routers.search._vector_metadata_rows", return_value=[]),
            patch("routers.search.get_chunk_store", return_value=None),
        ):
            response = client.get("/api/search", params={"keyword": "信息安全"})
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        results = body["data"]["results"]
        assert len(results) >= 1
        assert any(r["standard_no"] == "GB/T 90001-2020" for r in results)

    def test_search_suggest(self, client, sample_standard) -> None:
        with patch("routers.search._vector_metadata_rows", return_value=[]):
            response = client.get("/api/search/suggest", params={"keyword": "GB"})
        assert response.status_code == 200
        body = response.json()
        suggestions = body["data"]
        assert len(suggestions) >= 1
        assert any(s["type"] == "standard_no" for s in suggestions)

    def test_search_suggest_empty_keyword_rejected(self, client) -> None:
        response = client.get("/api/search/suggest", params={"keyword": ""})
        assert response.status_code == 422
