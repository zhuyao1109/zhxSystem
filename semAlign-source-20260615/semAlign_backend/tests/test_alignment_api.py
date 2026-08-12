"""对齐路由 API 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.alignment_task import AlignmentTask


class TestAlignmentTasksApi:
    def test_create_task_missing_groups(self, client) -> None:
        response = client.post(
            "/api/alignment/tasks",
            json={"text": "对齐测试", "options": {}},
        )
        assert response.status_code == 400

    def test_create_task_same_group_rejected(
        self, client, sample_standard, sample_standard_b
    ) -> None:
        sid = str(sample_standard.id)
        response = client.post(
            "/api/alignment/tasks",
            json={
                "text": "对齐测试",
                "options": {"group1Id": sid, "group2Id": sid},
            },
        )
        assert response.status_code == 400

    def test_create_and_list_tasks(
        self, client, memory_session, test_user, sample_standard, sample_standard_b
    ) -> None:
        with patch("routers.alignment._run_alignment_task_background"):
            response = client.post(
                "/api/alignment/tasks",
                json={
                    "text": "对齐测试",
                    "options": {
                        "group1Id": str(sample_standard.id),
                        "group2Id": str(sample_standard_b.id),
                    },
                },
            )
        assert response.status_code == 201
        task_id = response.json()["data"]["id"]

        listed = client.get("/api/alignment/tasks")
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] >= 1

        detail = client.get(f"/api/alignment/tasks/{task_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["status"] == "pending"

    def test_get_task_not_found(self, client) -> None:
        response = client.get("/api/alignment/tasks/99999")
        assert response.status_code == 404

    def test_save_and_delete_task(
        self, client, memory_session, test_user, sample_standard, sample_standard_b
    ) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
            options={"group1Id": str(sample_standard.id), "group2Id": str(sample_standard_b.id)},
            result_json={"conflicts": [{"id": "c1", "title": "冲突1"}]},
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        save_resp = client.post(f"/api/alignment/tasks/{task.id}/save")
        assert save_resp.status_code == 200

        del_resp = client.delete(f"/api/alignment/tasks/{task.id}")
        assert del_resp.status_code == 200

    def test_manual_mapping_accept(
        self, client, memory_session, test_user, sample_standard, sample_standard_b
    ) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
            result_json={"conflicts": [{"id": "c1", "title": "冲突1"}]},
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        response = client.post(
            f"/api/alignment/tasks/{task.id}/manual-mapping",
            json={"conflict_id": "c1", "decision": "accept", "notes": "同意"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["decision"] == "accept"

    def test_review_submit_and_publish(
        self, client, admin_client, memory_session, test_user, admin_user
    ) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
            review_status="draft",
            result_json={"conflicts": []},
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        submit = client.post(
            f"/api/alignment/tasks/{task.id}/review",
            json={"action": "submit", "notes": "请审核"},
        )
        assert submit.status_code == 200
        assert submit.json()["data"]["review_status"] == "submitted"

        approve = admin_client.post(
            f"/api/alignment/tasks/{task.id}/review",
            json={"action": "approve", "notes": "通过"},
        )
        assert approve.status_code == 200

        publish = admin_client.post(
            f"/api/alignment/tasks/{task.id}/review",
            json={"action": "publish"},
        )
        assert publish.status_code == 200
        assert publish.json()["data"]["review_status"] == "published"

        published = client.get("/api/alignment/published")
        assert published.status_code == 200
        assert published.json()["data"]["total"] >= 1

    def test_review_invalid_action(self, client, memory_session, test_user) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        response = client.post(
            f"/api/alignment/tasks/{task.id}/review",
            json={"action": "unknown"},
        )
        assert response.status_code == 400


    def test_retry_alignment_task(
        self, client, memory_session, test_user, sample_standard, sample_standard_b
    ) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="重试",
            status="failed",
            options={
                "group1Id": str(sample_standard.id),
                "group2Id": str(sample_standard_b.id),
            },
            result_json={"error": "old"},
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        with patch("routers.alignment._run_alignment_task_background"):
            response = client.post(f"/api/alignment/tasks/{task.id}/retry")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "pending"

    def test_manual_mapping_conflict_not_found(
        self, client, memory_session, test_user
    ) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
            result_json={"conflicts": []},
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        response = client.post(
            f"/api/alignment/tasks/{task.id}/manual-mapping",
            json={"conflict_id": "missing", "decision": "accept"},
        )
        assert response.status_code == 400

    def test_review_reject_requires_admin(self, client, memory_session, test_user) -> None:
        task = AlignmentTask(
            user_id=test_user.id,
            input_text="测试",
            status="completed",
            review_status="submitted",
        )
        memory_session.add(task)
        memory_session.commit()
        memory_session.refresh(task)

        response = client.post(
            f"/api/alignment/tasks/{task.id}/review",
            json={"action": "reject", "notes": "驳回"},
        )
        assert response.status_code == 403

    def test_chat_llm_fallback_hint(self, client) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("401 Invalid token")
        with (
            patch("routers.alignment._alignment_chat_use_llm", return_value=True),
            patch("routers.alignment._build_alignment_chat_llm", return_value=(mock_client, "m")),
            patch("routers.alignment.get_chunk_store", return_value=None),
        ):
            response = client.post("/api/alignment/chat", json={"message": "未知术语XYZ"})
        assert response.status_code == 200
        assert "未检索到" in response.json()["data"]["answer"] or "XYZ" in response.json()["data"]["answer"]


class TestAlignmentChatApi:
    def test_chat_empty_message_rejected(self, client) -> None:
        response = client.post("/api/alignment/chat", json={"message": "  "})
        assert response.status_code == 400

    def test_chat_vector_engine_greeting(self, client) -> None:
        with (
            patch("routers.alignment._alignment_chat_use_llm", return_value=False),
            patch("routers.alignment.get_chunk_store", return_value=None),
        ):
            response = client.post("/api/alignment/chat", json={"message": "你好"})
        assert response.status_code == 200
        assert "标准对齐助手" in response.json()["data"]["answer"]

    def test_chat_with_standard_hit(self, client, sample_standard) -> None:
        with (
            patch("routers.alignment._alignment_chat_use_llm", return_value=False),
            patch("routers.alignment.get_chunk_store", return_value=None),
        ):
            response = client.post(
                "/api/alignment/chat",
                json={"message": "信息安全管理制度"},
            )
        assert response.status_code == 200
        answer = response.json()["data"]["answer"]
        assert "GB/T 90001" in answer or "信息安全" in answer

    def test_chat_with_group_context(
        self, client, sample_standard, sample_standard_b
    ) -> None:
        with (
            patch("routers.alignment._alignment_chat_use_llm", return_value=False),
            patch("routers.alignment.get_chunk_store", return_value=None),
        ):
            response = client.post(
                "/api/alignment/chat",
                json={
                    "message": "这两条标准有什么差异",
                    "group1_id": str(sample_standard.id),
                    "group2_id": str(sample_standard_b.id),
                },
            )
        assert response.status_code == 200
        assert response.json()["data"]["answer"]

    def test_chat_llm_success(self, client) -> None:
        mock_message = MagicMock()
        mock_message.content = "LLM 回答"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_completions = MagicMock()
        mock_completions.create.return_value = mock_response
        mock_chat = MagicMock()
        mock_chat.completions = mock_completions
        mock_client = MagicMock()
        mock_client.chat = mock_chat

        with (
            patch("routers.alignment._alignment_chat_use_llm", return_value=True),
            patch("routers.alignment._build_alignment_chat_llm", return_value=(mock_client, "test-model")),
            patch("routers.alignment.get_chunk_store", return_value=None),
        ):
            response = client.post("/api/alignment/chat", json={"message": "测试问题"})
        assert response.status_code == 200
        assert response.json()["data"]["answer"] == "LLM 回答"
