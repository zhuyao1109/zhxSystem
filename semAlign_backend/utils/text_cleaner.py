"""解析文本的展示向清洗：去图片占位、压缩空白、修正 OCR 断字。"""

from __future__ import annotations

import re
import unicodedata

_NOISE_LINE_MARKERS = (
    "--- 图片",
    "[文件:",
    "[标题:",
    "[尺寸:",
)

_NOISE_BLOCK_PATTERN = re.compile(
    r"---\s*图片开始\s*---.*?---\s*图片结束\s*---",
    re.DOTALL,
)

_CJK_SPACE_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
_MULTI_BLANK_LINE = re.compile(r"\n{3,}")

# 封面/页眉页脚等噪声
_COVER_NOISE_RE = re.compile(
    r"^(?:"
    r"ICS[\d\s.]+"
    r"|中\s*华\s*人\s*民\s*共\s*和\s*国"
    r"|中华人民共和国"
    r"|国家质量监督检验检疫总局"
    r"|中国国家标准化管理委员会"
    r"|发\s*布"
    r"|实\s*施"
    r"|目\s*次"
    r"|前\s*言\s*$"
    r"|\d{4}[-/年]\d{1,2}[-/月]\d{1,2}"
    r")",
    re.I,
)

_SCOPE_SECTION_RE = re.compile(
    r"1\s*范围\s*(.+?)(?=2\s*规范性引用|2\s*引用文件|3\s*术语|4\s*原理|参考文献|$)",
    re.S,
)

_PREFACE_SECTION_RE = re.compile(
    r"前\s*言\s*(.+?)(?=1\s*范围|引言|目\s*次|$)",
    re.S,
)

_BOILERPLATE_PHRASES = (
    "本标准按照",
    "给出的规则起草",
    "本标准由",
    "本标准起草单位",
    "本标准主要起草人",
    "归口",
    "提出",
    "发布",
    "实施",
)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _drop_noise_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(marker in line for marker in _NOISE_LINE_MARKERS):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def _collapse_inline_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def clean_display_text(text: str | None, *, preserve_paragraphs: bool = False) -> str:
    """清洗供用户阅读/检索展示的文本。"""
    if not text:
        return ""

    cleaned = normalize_unicode(text)
    cleaned = _NOISE_BLOCK_PATTERN.sub("", cleaned)
    cleaned = _drop_noise_lines(cleaned)
    cleaned = _CJK_SPACE_PATTERN.sub("", cleaned)

    if preserve_paragraphs:
        paragraphs: list[str] = []
        for block in re.split(r"\n\s*\n", cleaned):
            line = _collapse_inline_whitespace(block.replace("\n", " "))
            if line:
                paragraphs.append(line)
        cleaned = "\n\n".join(paragraphs)
    else:
        cleaned = _collapse_inline_whitespace(cleaned.replace("\n", " "))

    cleaned = _MULTI_BLANK_LINE.sub("\n\n", cleaned)
    return cleaned.strip()


def clean_parsed_text(text: str | None) -> str:
    """入库/保存前的解析文本清洗（保留段落结构）。"""
    return clean_display_text(text, preserve_paragraphs=True)


def _truncate(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _is_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 6:
        return True
    if _COVER_NOISE_RE.match(stripped):
        return True
    if any(phrase in stripped for phrase in _BOILERPLATE_PHRASES):
        return True
    # 表格/符号碎片：字母数字占比过高且几乎无中文
    cjk = len(re.findall(r"[\u4e00-\u9fff]", stripped))
    if len(stripped) > 40 and cjk < 4:
        return True
    return False


def summarize_standard_text(text: str | None, max_len: int = 280) -> str:
    """
    从 PDF 解析全文中提取简短可读摘要，优先「范围」段落，其次前言实质内容。
    用于标准列表 description、搜索结果 fallback 等展示场景。
    """
    cleaned = clean_display_text(text, preserve_paragraphs=True)
    if not cleaned:
        return ""

    flat = cleaned.replace("\n\n", " ")

    scope_match = _SCOPE_SECTION_RE.search(flat)
    if scope_match:
        scope = clean_display_text(scope_match.group(1), preserve_paragraphs=False)
        if len(scope) >= 16:
            return _truncate(scope, max_len)

    preface_match = _PREFACE_SECTION_RE.search(cleaned)
    if preface_match:
        for sentence in re.split(r"[。！？；]", preface_match.group(1)):
            sentence = clean_display_text(sentence, preserve_paragraphs=False)
            if len(sentence) >= 16 and not _is_boilerplate_line(sentence):
                return _truncate(sentence + "。", max_len)

    picked: list[str] = []
    for line in cleaned.splitlines():
        line = clean_display_text(line, preserve_paragraphs=False)
        if _is_boilerplate_line(line):
            continue
        picked.append(line)
        joined = " ".join(picked)
        if len(joined) >= max_len:
            return _truncate(joined, max_len)

    joined = clean_display_text(" ".join(picked), preserve_paragraphs=False)
    if joined:
        return _truncate(joined, max_len)
    return _truncate(clean_display_text(text, preserve_paragraphs=False), max_len)


def format_excerpt(text: str | None, keyword: str = "", max_len: int = 220) -> str | None:
    """生成搜索结果摘要，尽量围绕关键词截取。"""
    cleaned = clean_display_text(text, preserve_paragraphs=False)
    if not cleaned:
        return None

    needle = (keyword or "").strip()
    if needle:
        idx = cleaned.lower().find(needle.lower())
        if idx >= 0:
            padding = max(0, max_len - len(needle))
            left = padding // 2
            start = max(0, idx - left)
            end = start + max_len
            if end > len(cleaned):
                end = len(cleaned)
                start = max(0, end - max_len)
            snippet = cleaned[start:end].strip()
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(cleaned) else ""
            return f"{prefix}{snippet}{suffix}"

    if len(cleaned) <= max_len:
        return cleaned
    summary = summarize_standard_text(cleaned, max_len=max_len)
    return summary or (_truncate(cleaned, max_len))
