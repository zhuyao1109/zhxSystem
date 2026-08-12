"""对齐助手辅助函数深度测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from routers.alignment import (
    _append_vector_blocks_for_chat,
    _build_alignment_chat_user_prompt,
    _build_chat_retrieval_context,
    _build_rule_fallback_chat_response,
    _build_vector_engine_chat_response,
    _dedupe_refs_preserve_order,
    _filter_relevant_chat_context,
    _format_context_block_for_answer,
    _lookup_builtin_term_brief,
    _query_standard_blocks_for_chat,
    _validate_alignment_target_value,
)
from schemas.base import APIResponse


class TestAlignmentHelperFunctions:
    def test_dedupe_refs(self):
        refs = ["a", "b", "a", "c", "b"]
        assert _dedupe_refs_preserve_order(refs) == ["a", "b", "c"]

    def test_format_context_block(self):
        block = "[标准1] GB/T 1\n这是条款正文内容"
        formatted = _format_context_block_for_answer(block)
        assert "标准1" in formatted
        assert "条款" in formatted

    def test_filter_relevant_chat_context(self):
        blocks = [
            "[标准1] GB/T 1\n包含信息安全内容",
            "[标准2] GB/T 2\n无关内容",
        ]
        refs = ["r1", "r2"]
        fb, fr = _filter_relevant_chat_context(blocks, refs, "信息安全")
        assert len(fb) == 1
        assert fr == ["r1"]

    def test_build_user_prompt_with_and_without_context(self):
        with_ctx = _build_alignment_chat_user_prompt("问题", ["[片段] a\n正文"])
        without = _build_alignment_chat_user_prompt("问题", [])
        assert "可用上下文" in with_ctx
        assert "没有选定标准" in without

    def test_vector_engine_with_context_blocks(self):
        blocks = ["[标准1] GB/T 1\n信息安全管理制度要求"]
        resp = _build_vector_engine_chat_response("问题", blocks, ["GB/T 1"])
        assert isinstance(resp, APIResponse)
        assert "信息安全" in resp.data.answer

    def test_vector_engine_builtin_osi(self):
        resp = _build_vector_engine_chat_response("OSI协议", [], [])
        assert "OSI" in resp.data.answer or "七层" in resp.data.answer
        assert _lookup_builtin_term_brief("osi协议")

    def test_rule_fallback_with_db_hits(self, memory_session, sample_standard):
        resp = _build_rule_fallback_chat_response(
            "信息安全",
            memory_session,
        )
        assert resp.data.references
        assert "GB/T 90001" in resp.data.references[0]

    def test_query_standard_blocks(self, memory_session, sample_standard):
        blocks, refs = _query_standard_blocks_for_chat("信息安全", memory_session, 3)
        assert blocks
        assert refs

    def test_build_chat_retrieval_context(self, memory_session, sample_standard):
        with patch("routers.alignment.get_chunk_store", return_value=None):
            blocks, refs = _build_chat_retrieval_context("信息安全", memory_session)
        assert blocks

    def test_append_vector_blocks(self):
        blocks: list[str] = []
        refs: list[str] = []
        store = MagicMock()
        store.retrieve.return_value = [
            {"page_content": "向量片段正文", "metadata": {"source_file": "a.pdf"}},
        ]
        _append_vector_blocks_for_chat("测试", 2, blocks, refs)
        assert blocks
        assert refs

    def test_validate_alignment_target_value(self):
        assert _validate_alignment_target_value(" 12 ") == "12"
