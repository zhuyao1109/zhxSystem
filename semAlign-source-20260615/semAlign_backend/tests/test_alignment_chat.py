"""对齐助手聊天辅助函数测试"""

from routers.alignment import (
    _extract_chat_query,
    _is_pure_greeting_message,
    _extract_chat_keywords,
)


class TestChatQueryExtraction:
    def test_pure_greeting(self):
        assert _is_pure_greeting_message("你好")
        assert _is_pure_greeting_message("您好")
        assert _extract_chat_query("你好") == ""

    def test_greeting_with_question(self):
        assert not _is_pure_greeting_message("你好，请问你知道OSI协议吗")
        assert "OSI" in _extract_chat_query("你好，请问你知道OSI协议吗")

    def test_keywords_from_compound_message(self):
        keywords = _extract_chat_keywords("你好，请问你知道OSI协议吗")
        assert any("OSI" in kw for kw in keywords)

    def test_builtin_osi_brief(self):
        from routers.alignment import _lookup_builtin_term_brief

        assert _lookup_builtin_term_brief("OSI协议") is not None
        assert "七层" in _lookup_builtin_term_brief("osi")
