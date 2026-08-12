"""对齐执行器单元测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.alignment_executor import (
    _align_pairs,
    _align_pairs_with_fallback,
    _build_solution,
    _build_standard_meta,
    _clause_from_part,
    _collect_page_marks,
    _ensure_effective_text,
    _extract_year,
    _fallback_similarity,
    _is_effective_text,
    _is_international,
    _is_mandatory_standard,
    _join_chunk_texts,
    _load_chunks_from_store,
    _load_standard_text,
    _load_text_by_standard_no,
    _load_text_by_suffix,
    _page_for_position,
    _priority_config_from_selected,
    _priority_score,
    _severity,
    _split_clauses,
    _split_raw_parts,
    _tokenize,
    run_alignment,
    _Clause,
)


LONG_TEXT_A = (
    "1.1 组织应建立信息安全管理制度并明确管理职责。"
    "1.2 组织应定期开展信息安全风险评估并保留评估记录。"
    "1.3 组织应对重要信息资产实施访问控制与审计。"
)

LONG_TEXT_B = (
    "2.1 组织必须建立信息安全控制措施并明确责任人。"
    "2.2 组织应每年开展一次安全审计并提交审计报告。"
    "2.3 组织应对关键系统实施访问控制与日志审计。"
)


def _make_standard(**kwargs) -> SimpleNamespace:
    defaults = {
        "id": 1,
        "standard_no": "GB/T 90001-2020",
        "name": "测试标准A",
        "status": "有效",
        "description": LONG_TEXT_A,
        "source_file": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestAlignmentExecutorHelpers:
    def test_clean_and_effective_text(self):
        assert _is_effective_text("x" * 120)
        assert not _is_effective_text("short")

    def test_tokenize_and_similarity(self):
        ta = _tokenize("信息安全 管理")
        tb = _tokenize("信息安全 管理 体系")
        assert ta & tb
        score = _fallback_similarity("信息安全管理制度", "信息安全管理规范")
        assert 0.0 < score < 1.0

    def test_split_clauses_numbered(self):
        clauses = _split_clauses(LONG_TEXT_A, max_count=10)
        assert len(clauses) >= 2
        assert all(isinstance(c, _Clause) for c in clauses)

    def test_split_raw_parts_and_clause_from_part(self):
        parts = _split_raw_parts(LONG_TEXT_A)
        assert parts
        seen: set[str] = set()
        clause = _clause_from_part(0, parts[0][1], [], seen, 0)
        assert clause is not None
        assert clause.section

    def test_severity_and_year(self):
        assert _severity(0.3) == "高冲突"
        assert _severity(0.5) == "中冲突"
        assert _severity(0.8) == "低冲突"
        assert _extract_year("GB/T 90001-2020") == 2020

    def test_standard_meta(self):
        iso = _build_standard_meta(_make_standard(standard_no="ISO 27001", name="国际"))
        gb = _build_standard_meta(_make_standard(standard_no="GB 12345", status="强制"))
        assert iso["publisher"] == "international"
        assert gb["standard_type"] == "mandatory"
        assert _is_international("ISO 9001", "质量管理")
        assert _is_mandatory_standard("GB 12345", "强制")

    def test_priority_config_and_score(self):
        cfg = _priority_config_from_selected(["international", "latest"])
        assert cfg["enabled_rules"]["international_priority"] is True
        pair = {"a_text": "必须执行", "b_text": "应当执行"}
        score = _priority_score(
            0.4,
            pair,
            ["comprehensive"],
            {"confidence": 0.8},
        )
        assert score > 0

    def test_build_solution(self):
        solution = _build_solution(
            {
                "id": "c1",
                "title": "术语冲突",
                "severity": "高冲突",
                "standard1": {"name": "A"},
                "standard2": {"name": "B"},
            },
            0,
        )
        assert solution["conflict_id"] == "c1"
        assert "A" in solution["description"]

    def test_align_pairs_with_fallback(self):
        ca = _Clause(idx=0, text="组织应建立信息安全管理制度", section="1.1", page=1)
        cb = _Clause(idx=0, text="组织应建立信息安全管理制度并持续改进", section="1.1", page=1)
        pairs = _align_pairs_with_fallback([ca], [cb], sim_threshold=0.3)
        assert len(pairs) == 1
        assert pairs[0]["score"] > 0

    def test_load_standard_text_from_description(self):
        text = _load_standard_text(_make_standard())
        assert "信息安全" in text

    def test_ensure_effective_text_ok(self):
        _ensure_effective_text(LONG_TEXT_A, "标准A")

    def test_ensure_effective_text_insufficient_clauses(self):
        single = "1.1 这是一条足够长的单条款文本，用于触发条款数量不足的错误提示。" * 2
        with pytest.raises(ValueError, match="至少需要 2 条"):
            _ensure_effective_text(single, "标准A")

    def test_load_from_chroma_sqlite_empty(self):
        from services.alignment_executor import _load_from_chroma_sqlite

        with patch("services.alignment_executor._chroma_db_path", return_value=Path("/nonexistent/chroma.sqlite3")):
            assert _load_from_chroma_sqlite(sid=1, file_id=None, source_file=None, source_base=None) == []

    def test_priority_config_empty_rules(self):
        cfg = _priority_config_from_selected([])
        assert cfg["enabled_rules"]["international_priority"] is True

    def test_build_standard_meta_no_year(self):
        meta = _build_standard_meta(_make_standard(standard_no="CUSTOM"))
        assert meta["publish_date"] == ""

    def test_join_chunks_and_load_from_store(self):
        chunks = _join_chunk_texts(
            [{"page_content": "第一段"}, {"page_content": ""}, {"other": "x"}]
        )
        assert "第一段" in chunks

        store = MagicMock()
        store.list_chunks.side_effect = [
            [],
            [{"page_content": "来自 store"}],
        ]
        rows = _load_chunks_from_store(
            store,
            sid=1,
            file_id="f1",
            source_file="a.pdf",
            source_base="a",
        )
        assert rows[0]["page_content"] == "来自 store"

    def test_load_text_helpers(self, tmp_path, monkeypatch):
        from services import alignment_executor as ae

        text_dir = tmp_path / "text_out"
        text_dir.mkdir()
        (text_dir / "doc_标准A.txt").write_text("GB/T 90001-2020 正文内容", encoding="utf-8")
        (text_dir / "other.txt").write_text("CUSTOM 标准全文", encoding="utf-8")
        monkeypatch.setattr(ae, "_text_output_dir", lambda: text_dir)

        by_suffix = _load_text_by_suffix("标准A.pdf")
        assert "GB/T 90001" in by_suffix
        by_no = _load_text_by_standard_no("CUSTOM")
        assert "标准全文" in by_no

    def test_page_mark_helpers(self):
        text = "前言 第1页 正文 page 2 结尾"
        marks = _collect_page_marks(text)
        assert marks
        assert _page_for_position(marks, 5) == 1
        assert _page_for_position(marks, len(text)) == 2

    def test_align_pairs_with_clause_aligner(self):
        ca = _Clause(idx=0, text="组织应建立信息安全管理制度", section="1.1", page=1)
        cb = _Clause(idx=0, text="组织应建立信息安全管理制度并持续改进", section="1.1", page=1)
        fake_aligner = MagicMock()
        fake_aligner.align_clauses.return_value = [
            {
                "clause_a": {"id": 0, "text": ca.text, "section": "1.1"},
                "clause_b": {"id": 0, "text": cb.text, "section": "1.1"},
                "similarity_score": 0.91,
                "match_type": "semantic",
            }
        ]
        with patch("services.alignment_executor._ALIGNER_AVAILABLE", True), patch(
            "services.alignment_executor.ClauseAligner", return_value=fake_aligner
        ):
            pairs = _align_pairs([ca], [cb], sim_threshold=0.3)
        assert pairs[0]["score"] == 0.91


class TestRunAlignment:
    def test_run_alignment_produces_conflicts(self):
        std_a = _make_standard(id=1, name="标准A", description=LONG_TEXT_A)
        std_b = _make_standard(
            id=2,
            standard_no="ISO/IEC 27001:2022",
            name="标准B",
            description=LONG_TEXT_B,
        )
        result = run_alignment(
            std_a,
            std_b,
            options={"similarityThreshold": 0.2, "enableLayer3": False},
            standards_catalog=[],
        )
        assert "conflicts" in result
        assert "stats" in result
        assert result["meta"]["aligner"] in {"ClauseAligner", "fallback"}
