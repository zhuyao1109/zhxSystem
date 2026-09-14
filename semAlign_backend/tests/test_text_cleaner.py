"""text_cleaner 单元测试。"""

from utils.text_cleaner import clean_display_text, clean_parsed_text, format_excerpt, summarize_standard_text


class TestTextCleaner:
    def test_removes_image_markers(self) -> None:
        raw = (
            "3.1 范围\n"
            "--- 图片开始 ---\n"
            "[文件: page1_img1.png]\n"
            "[标题: 图1]\n"
            "--- 图片结束 ---\n"
            "本标准适用于信息安全管理。"
        )
        cleaned = clean_display_text(raw)
        assert "--- 图片" not in cleaned
        assert "[文件:" not in cleaned
        assert "本标准适用于信息安全管理" in cleaned

    def test_fixes_cjk_spacing(self) -> None:
        assert clean_display_text("信 息 安 全") == "信息安全"

    def test_clean_parsed_text_preserves_paragraphs(self) -> None:
        raw = (
            "中 华 人 民 共 和 国 国 家 标 准\n"
            "\n"
            "1 范围\n"
            "本标准规定了信息安全管理的基本要求。\n"
            "本标准适用于各类组织的信息安全管理活动。\n"
            "\n"
            "2 规范性引用文件\n"
            "下列文件对于本文件的应用是必不可少的。\n"
            "--- 图片开始 ---\n"
            "[文件: page1_img1.png]\n"
            "--- 图片结束 ---\n"
            "3 术语和定义\n"
        )
        cleaned = clean_parsed_text(raw)
        assert "--- 图片" not in cleaned
        assert "中华人民共和国国家标准" in cleaned
        assert "1 范围" in cleaned
        assert "2 规范性引用文件" in cleaned
        # 关键：不能再把全文压成一行
        assert cleaned.count("\n") >= 3
        assert "本标准规定了信息安全管理的基本要求。" in cleaned

    def test_format_excerpt_around_keyword(self) -> None:
        text = "A" * 80 + "信息安全" + "B" * 80
        excerpt = format_excerpt(text, keyword="信息安全", max_len=60)
        assert excerpt is not None
        assert "信息安全" in excerpt
        assert excerpt.startswith("…") or excerpt.endswith("…")

    def test_summarize_standard_skips_cover_page(self) -> None:
        raw = (
            "ICS61020 . Y75 中 华 人 民 共 和 国 国 家 标 准 GB/T30548—2014\n"
            "服装用人体数据验证方法\n"
            "2014-05-06发布 2015-03-01实施\n"
            "前 言\n"
            "本标准按照 GB/T1.1—2009 给出的规则起草。\n"
            "1 范围\n"
            "本标准规定了用三维测量仪获取的服装用人体数据的验证方法。\n"
            "本标准适用于用三维测量仪获取的各类服装用人体数据的验证。"
        )
        summary = summarize_standard_text(raw, max_len=120)
        assert len(summary) <= 121
        assert "三维测量仪" in summary
        assert "ICS61020" not in summary
        assert "给出的规则起草" not in summary

    def test_summarize_skips_toc_only_text(self) -> None:
        raw = (
            "GB/T35311—2017\n中文新闻图片内容描述元数据规范\n目次\n"
            "范围 1 规范性引用文件 2 缩略语 3 元数据元素的属性约定 4\n"
            "图片内容元数据元素定义 5 5.1公共元数据\n"
        )
        assert summarize_standard_text(raw, max_len=120) == ""
