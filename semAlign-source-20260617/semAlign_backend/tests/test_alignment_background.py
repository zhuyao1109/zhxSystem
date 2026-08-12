"""对齐后台任务与 LLM 配置测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from core.config import settings
from models.alignment_task import AlignmentTask
from routers.alignment import (
    _build_alignment_chat_llm,
    _run_alignment_task_background,
    _validate_alignment_target_value,
)


class TestAlignmentBackgroundAndLlm:
    def test_validate_alignment_target_empty(self):
        with pytest.raises(HTTPException):
            _validate_alignment_target_value(None)
        with pytest.raises(HTTPException):
            _validate_alignment_target_value("  ")

    def test_build_alignment_chat_llm_deepseek(self, monkeypatch):
        monkeypatch.setattr(settings, "fourz_api_key", None)
        monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
        client, model = _build_alignment_chat_llm()
        assert client is not None
        assert "deepseek" in model

    def test_build_alignment_chat_llm_none(self, monkeypatch):
        monkeypatch.setattr(settings, "fourz_api_key", None)
        monkeypatch.setattr(settings, "deepseek_api_key", None)
        client, model = _build_alignment_chat_llm()
        assert client is None
        assert model == ""

    def test_run_alignment_task_background_success(
        self, memory_session, test_user, sample_standard, sample_standard_b
    ):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="后台任务",
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

        fake_result = {"conflicts": [], "stats": {"conflict_rate": 0}}
        session_factory = MagicMock(return_value=memory_session)
        with (
            patch("routers.alignment.SessionLocal", session_factory),
            patch("routers.alignment.run_alignment", return_value=fake_result),
        ):
            _run_alignment_task_background(task_id)

        updated = memory_session.query(AlignmentTask).filter(AlignmentTask.id == task_id).first()
        assert updated is not None
        assert updated.status == "completed"
        assert updated.result_json == fake_result

    def test_run_alignment_task_background_missing_task(self, memory_session):
        session_factory = MagicMock(return_value=memory_session)
        with patch("routers.alignment.SessionLocal", session_factory):
            _run_alignment_task_background(99999)

    def test_run_alignment_task_background_value_error(
        self, memory_session, test_user, sample_standard, sample_standard_b
    ):
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="后台任务",
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
            patch("routers.alignment.run_alignment", side_effect=ValueError("文本无效")),
        ):
            _run_alignment_task_background(task_id)

        updated = memory_session.query(AlignmentTask).filter(AlignmentTask.id == task_id).first()
        assert updated is not None
        assert updated.status == "failed"
        assert "文本无效" in updated.result_json.get("error", "")
