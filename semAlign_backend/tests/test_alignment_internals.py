"""对齐路由内部函数测试（提升覆盖率）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from core.config import settings
from routers.alignment import (
    _append_vector_blocks_for_chat,
    _build_alignment_chat_llm,
    _build_alignment_chat_user_prompt,
    _build_chat_context_from_target,
    _chroma_sqlite_has_embedding_source,
    _dedupe_refs_preserve_order,
    _filter_relevant_context_blocks,
    _is_pure_greeting_message,
    _lookup_builtin_term_brief,
    _resolve_alignment_target,
    _resolve_db_standard_target,
    _resolve_vector_alignment_target,
    _run_alignment_task_background,
    _try_llm_alignment_chat,
)
from models.alignment_task import AlignmentTask


class TestAlignmentRouterInternals:
    def test_build_alignment_chat_llm_fourz(self, monkeypatch):
        monkeypatch.setattr(settings, "fourz_api_key", "fz-key")
        monkeypatch.setattr(settings, "fourz_api_base", "http://example/v1")
        client, model = _build_alignment_chat_llm()
        assert client is not None
        assert model

    def test_resolve_db_standard_not_found(self, memory_session):
        with pytest.raises(HTTPException) as exc:
            _resolve_db_standard_target(99999, memory_session)
        assert exc.value.status_code == 404

    def test_resolve_alignment_target_by_id(self, memory_session, sample_standard):
        target = _resolve_alignment_target(str(sample_standard.id), memory_session)
        assert target.id == sample_standard.id

    def test_resolve_vector_target_with_saved_text(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.document_processor.settings.text_output_dir", str(tmp_path))
        (tmp_path / "doc.txt").write_text("saved", encoding="utf-8")
        with patch("routers.alignment.get_chunk_store", return_value=None):
            target = _resolve_vector_alignment_target("doc.pdf")
        assert target.name == "doc.pdf"

    def test_resolve_vector_target_missing(self):
        with (
            patch("routers.alignment.get_chunk_store", return_value=MagicMock(list_chunks=lambda *a, **k: [])),
            patch("routers.alignment.DocumentProcessor") as mock_proc,
            patch("routers.alignment._chroma_sqlite_has_embedding_source", return_value=False),
        ):
            mock_proc.return_value.load_saved_text.return_value = None
            with pytest.raises(HTTPException) as exc:
                _resolve_vector_alignment_target("missing.pdf")
        assert exc.value.status_code == 404

    def test_resolve_alignment_target_vector_prefix(self):
        with patch("routers.alignment._resolve_vector_alignment_target") as mock_vec:
            mock_vec.return_value = object()
            assert _resolve_alignment_target("vector:demo.pdf", MagicMock()) is mock_vec.return_value

    def test_chroma_sqlite_has_embedding_source(self, tmp_path, monkeypatch):
        chroma_dir = tmp_path / "chroma"
        chroma_dir.mkdir()
        db_path = chroma_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "create table embedding_metadata (key text, string_value text)"
        )
        conn.execute(
            "insert into embedding_metadata values ('source', 'demo.pdf')"
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(settings, "chroma_db_dir", str(chroma_dir))
        assert _chroma_sqlite_has_embedding_source("demo.pdf")
        assert not _chroma_sqlite_has_embedding_source("other.pdf")

    def test_build_chat_context_from_target(self, sample_standard):
        with patch("routers.alignment._load_standard_text", return_value="标准正文" * 30):
            label, excerpt = _build_chat_context_from_target(sample_standard)
        assert "GB/T" in label
        assert excerpt

    def test_try_llm_alignment_chat_returns_response(self):
        mock_message = MagicMock(content="回答")
        mock_response = MagicMock(choices=[MagicMock(message=mock_message)])
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        with patch("routers.alignment._build_alignment_chat_llm", return_value=(mock_client, "m")):
            resp, hint = _try_llm_alignment_chat("问题", [], [])
        assert resp is not None
        assert hint == ""

    def test_try_llm_alignment_chat_no_client(self):
        with patch("routers.alignment._build_alignment_chat_llm", return_value=(None, "")):
            resp, hint = _try_llm_alignment_chat("问题", [], [])
        assert resp is None

    def test_run_alignment_task_background_generic_exception(
        self, memory_session, test_user, sample_standard, sample_standard_b
    ):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="x",
            status="pending",
            options={
                "group1Id": str(sample_standard.id),
                "group2Id": str(sample_standard_b.id),
            },
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)
        task_id = task.id
        session_factory = MagicMock(return_value=memory_session)
        with (
            patch("routers.alignment.SessionLocal", session_factory),
            patch("routers.alignment.run_alignment", side_effect=RuntimeError("boom")),
        ):
            _run_alignment_task_background(task_id)
        updated = memory_session.query(AlignmentTask).filter(AlignmentTask.id == task_id).first()
        assert updated.status == "failed"

    def test_resolve_alignment_target_invalid_vector(self):
        with pytest.raises(HTTPException):
            _resolve_alignment_target("vector:", MagicMock())

    def test_misc_chat_helpers(self):
        assert _is_pure_greeting_message("你好")
        assert _lookup_builtin_term_brief("tcp ip")
        assert _dedupe_refs_preserve_order(["a", "a"]) == ["a"]
        blocks = _filter_relevant_context_blocks(["[x] OSI\n正文"], "OSI")
        assert blocks
        refs: list[str] = []
        blks: list[str] = []
        store = MagicMock()
        store.retrieve.return_value = []
        with patch("routers.alignment.get_chunk_store", return_value=store):
            _append_vector_blocks_for_chat("x", 0, blks, refs)
        assert _build_alignment_chat_user_prompt("q", ["ctx"])
