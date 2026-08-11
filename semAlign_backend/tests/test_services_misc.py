"""服务层与工具函数测试。"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

from services.comparison_payloads import (
    get_comparison_stats_payload,
    get_comparison_task_payload,
    get_conflicts_payload,
    get_feedback_counts,
    get_modifications_payload,
    get_semantic_clusters_payload,
    get_solutions_payload,
)
from services.export_report import build_report_excel_bytes
from services.rule_service import (
    default_rule_config,
    evaluate_conflict_request,
    list_rules_payload,
)
from utils.file_utils import (
    get_file_extension,
    is_supported_format,
    save_uploaded_file,
)
from utils.validation import validate_conflict, validate_metadata


class TestComparisonPayloads:
    def test_all_payload_helpers(self):
        assert get_comparison_task_payload("t1")["id"] == "t1"
        stats = get_comparison_stats_payload()
        assert stats["conflict_rate"] == 32
        assert len(get_semantic_clusters_payload()) >= 1
        assert len(get_conflicts_payload()) >= 1
        assert len(get_solutions_payload()) >= 1
        assert get_feedback_counts("conflict-1")["approve"] == 12
        assert get_modifications_payload("t1")["task_id"] == "t1"


class TestExportReport:
    def test_build_report_excel_bytes(self):
        data, filename = build_report_excel_bytes("task-001")
        assert data[:2] == b"PK"
        assert filename.endswith(".xlsx")
        assert "task-001" in filename


class TestRuleService:
    def test_default_config_and_list(self):
        cfg = default_rule_config()
        assert cfg["enabled_rules"]["international_priority"] is True
        rules = list_rules_payload()
        assert len(rules["rules"]) == 3

    def test_evaluate_conflict_request(self):
        request = {
            "conflict": {
                "id": "c1",
                "clause_a": {
                    "text": "ISO international standard text",
                    "standard_no": "ISO 9001",
                    "publish_date": "2020-01-01",
                },
                "clause_b": {
                    "text": "GB domestic standard text",
                    "standard_no": "GB/T 9001",
                    "publish_date": "2018-01-01",
                },
            },
            "config": default_rule_config(),
        }
        result = evaluate_conflict_request(request)
        assert result["conflict_id"] == "c1"
        assert "final_recommendation" in result


class TestValidationUtils:
    def test_validate_metadata_ok(self):
        ok, msg = validate_metadata({"document_name": "doc", "publisher": "pub"})
        assert ok and msg == ""

    def test_validate_metadata_missing(self):
        ok, msg = validate_metadata({"document_name": ""})
        assert not ok

    def test_validate_conflict_ok(self):
        ok, msg = validate_conflict(
            {
                "conflict_id": "1",
                "clause_a": {},
                "clause_b": {},
                "conflict_type": "semantic",
            }
        )
        assert ok

    def test_validate_conflict_missing(self):
        ok, msg = validate_conflict({"conflict_id": "1"})
        assert not ok


class TestFileUtils:
    def test_extension_and_supported(self, tmp_path: Path):
        f = tmp_path / "demo.pdf"
        f.write_bytes(b"%PDF")
        assert get_file_extension(str(f)) == ".pdf"
        assert is_supported_format(str(f))
        assert not is_supported_format(str(tmp_path / "demo.bin"))

    def test_cleanup_temp_files(self, tmp_path, monkeypatch):
        from utils import file_utils

        temp_file = tmp_path / "upload_test.tmp"
        temp_file.write_text("x", encoding="utf-8")
        upload_dir = tmp_path / "upload_abc123"
        upload_dir.mkdir()
        (upload_dir / "nested.txt").write_text("nested", encoding="utf-8")
        monkeypatch.setattr(file_utils.tempfile, "gettempdir", lambda: str(tmp_path))
        file_utils.cleanup_temp_files()
        assert not temp_file.exists()
        assert not upload_dir.exists()
        uploaded = MagicMock()
        uploaded.name = "test.pdf"
        uploaded.getbuffer.return_value = io.BytesIO(b"hello").getvalue()
        path = save_uploaded_file(uploaded)
        assert Path(path).exists()
        assert path.endswith(".pdf")
