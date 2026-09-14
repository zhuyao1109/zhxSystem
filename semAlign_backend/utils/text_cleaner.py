"""解析文本的展示向清洗：去图片占位、压缩空白、修正 OCR 断字，并保留段落结构。"""

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
_PAGE_NUM_ONLY = re.compile(r"^(?:\d+|[ivxlcdmⅣⅰⅴⅹⅼⅽⅾⅿ]+)$", re.I)
_DOT_LEADER = re.compile(r"[·•．.]{3,}|\.{3,}|…{2,}|…+")
_REPEATED_HEADER = re.compile(
    r"^(?:GB/?T?\s*[\d.]+(?:—|-)\d{4}|中华人民共和国国家标准)\s*$",
    re.I,
)

# 封面/页眉页脚等噪声（用于摘要，不用于全文删除）
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
    r"(?:^|[\s\d.])*?(?:范围)\s*(.+?)(?=\d+\s*规范性引用|\d+\s*引用文件|\d+\s*术语|\d+\s*原理|参考文献|$)",
    re.S,
)

_PREFACE_SECTION_RE = re.compile(
    r"前\s*言\s*(.+?)(?=\d+\s*范围|引言|目\s*次|$)",
    re.S,
)

_NORMATIVE_SENTENCE_RE = re.compile(
    r"((?:本文件|本标准|本规范|本指导性技术文件)(?:规定了|适用于|确立了|界定了|给出了)[^。！？；\n]{8,200}[。！？；]?)"
)

_TOC_LIKE_RE = re.compile(
    r"(?:"
    r"目\s*次|"
    r"引言\s*范围|"
    r"范围\s*1\s*规范性引用|"
    r"规范性引用文件\s*2|"
    r"术语和定义\s*3|"
    r"\.{3,}|"
    r"·{3,}"
    r")"
)

_BOILERPLATE_PHRASES = (
    "本标准按照",
    "本文件按照",
    "给出的规则起草",
    "本标准由",
    "本文件由",
    "本标准起草单位",
    "本文件起草单位",
    "本标准主要起草人",
    "本文件主要起草人",
    "归口",
    "提出",
    "发布",
    "实施",
)

_HEADING_HINT = re.compile(
    r"^(?:"
    r"第?[一二三四五六七八九十百千零〇两\d]+[章节条款篇部分]"
    r"|\d+(?:\.\d+){0,4}"
    r"|附录\s*[A-Z]"
    r"|目\s*次|前\s*言|引\s*言|范围|规范性引用文件|术语和定义|参考文献"
    r")\s*"
)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _collapse_inline_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _drop_noise_lines(text: str, *, keep_blank_lines: bool = True) -> str:
    """去掉图片占位行；默认保留空行，以免毁掉段落边界。"""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if keep_blank_lines:
                kept.append("")
            continue
        if any(marker in line for marker in _NOISE_LINE_MARKERS):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def _looks_like_heading(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    if len(text) <= 40 and _HEADING_HINT.match(text):
        return True
    if _PAGE_NUM_ONLY.match(text):
        return True
    if _REPEATED_HEADER.match(text):
        return True
    return False


def _ends_sentence(line: str) -> bool:
    return bool(re.search(r"[。！？；：:.!?…」』）)\]]\s*$", line.strip()))


def _should_join_soft_wrap(prev: str, curr: str) -> bool:
    """判断两行是否为 PDF 软换行（应合并），而非新段落/标题。"""
    prev = prev.strip()
    curr = curr.strip()
    if not prev or not curr:
        return False
    if _looks_like_heading(prev) or _looks_like_heading(curr):
        return False
    if _ends_sentence(prev):
        return False
    if _DOT_LEADER.search(prev) or _DOT_LEADER.search(curr):
        return False
    if _PAGE_NUM_ONLY.match(curr):
        return False
    # 目次常见「标题 / 页码」分行，不要并成「范围 1」
    if len(prev) <= 20 and _PAGE_NUM_ONLY.match(curr):
        return False
    # 过短的上一行更像独立标题
    if len(prev) <= 8 and not re.search(r"[，、；：,.]$", prev):
        return False
    return True


def _join_soft_wrap(prev: str, curr: str) -> str:
    if re.search(r"[\u4e00-\u9fff]$", prev) and re.search(r"^[\u4e00-\u9fff]", curr):
        return prev + curr
    if prev.endswith("-") and re.match(r"^[A-Za-z]", curr):
        return prev[:-1] + curr
    return f"{prev} {curr}"


def _merge_soft_wraps(text: str) -> str:
    """合并段落内软换行，同时保留空行与标题行。"""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if not out or out[-1] == "":
            out.append(line)
            continue
        if _should_join_soft_wrap(out[-1], line):
            out[-1] = _join_soft_wrap(out[-1], line)
        else:
            out.append(line)
    return "\n".join(out)


def _dedupe_consecutive_headers(text: str) -> str:
    """去掉连续重复的页眉短行（如每页重复的 GB/T 编号）。"""
    out: list[str] = []
    prev_header = ""
    for line in text.splitlines():
        stripped = line.strip()
        if _REPEATED_HEADER.match(stripped):
            if stripped == prev_header:
                continue
            prev_header = stripped
            out.append(stripped)
            continue
        if stripped:
            prev_header = ""
        out.append(stripped)
    return "\n".join(out)


def clean_display_text(text: str | None, *, preserve_paragraphs: bool = False) -> str:
    """清洗供用户阅读/检索展示的文本。

    preserve_paragraphs=True 时保留换行与段落（用于解析全文预览/入库）；
    False 时压成单行（用于摘要、搜索 snippet）。
    """
    if not text:
        return ""

    cleaned = normalize_unicode(text)
    cleaned = _NOISE_BLOCK_PATTERN.sub("\n\n", cleaned)
    cleaned = _drop_noise_lines(cleaned, keep_blank_lines=True)
    cleaned = _CJK_SPACE_PATTERN.sub("", cleaned)

    if preserve_paragraphs:
        lines: list[str] = []
        for line in cleaned.splitlines():
            if not line.strip():
                lines.append("")
                continue
            lines.append(_collapse_inline_whitespace(line))
        cleaned = "\n".join(lines)
        cleaned = _merge_soft_wraps(cleaned)
        cleaned = _dedupe_consecutive_headers(cleaned)
        cleaned = _CJK_SPACE_PATTERN.sub("", cleaned)
        cleaned = _MULTI_BLANK_LINE.sub("\n\n", cleaned)
    else:
        cleaned = _collapse_inline_whitespace(cleaned.replace("\n", " "))
        cleaned = _CJK_SPACE_PATTERN.sub("", cleaned)

    return cleaned.strip()


def clean_parsed_text(text: str | None) -> str:
    """入库/保存前的解析文本清洗（保留段落结构）。"""
    return clean_display_text(text, preserve_paragraphs=True)


def _truncate(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


_PUBLISHER_LIKE_RE = re.compile(
    r"(?:国家标准化管理委员会|国家市场监督管理总局|国家质量监督检验检疫总局)"
)


def _is_toc_like_text(text: str) -> bool:
    sample = (text or "").strip()
    if not sample:
        return True
    if _TOC_LIKE_RE.search(sample[:160]):
        return True
    # 无实质规范句，却有大量章节编号/附录 → 目次
    has_norm = bool(re.search(r"(规定了|适用于|确立了|界定了|本文件是)", sample))
    if not has_norm:
        numbered = len(re.findall(r"\d+(?:\.\d+)+", sample))
        if numbered >= 3:
            return True
        if "附录" in sample or "参考文献" in sample:
            return True
        if len(re.findall(r"\b\d+\b", sample)) >= 6 and len(sample) < 500:
            return True
    return False


def _is_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 6:
        return True
    if _COVER_NOISE_RE.match(stripped):
        return True
    if any(phrase in stripped for phrase in _BOILERPLATE_PHRASES):
        return True
    if _PUBLISHER_LIKE_RE.search(stripped) and len(stripped) <= 24:
        return True
    if _is_toc_like_text(stripped) and len(stripped) < 80:
        return True
    # 表格/符号碎片：字母数字占比过高且几乎无中文
    cjk = len(re.findall(r"[\u4e00-\u9fff]", stripped))
    if len(stripped) > 40 and cjk < 4:
        return True
    return False


def summarize_standard_text(text: str | None, max_len: int = 280) -> str:
    """
    从 PDF 解析全文中提取简短可读摘要，优先「本文件/本标准规定了…」，
    其次「范围」段落；避免把封面/目次当成描述。
    """
    cleaned = clean_display_text(text, preserve_paragraphs=True)
    if not cleaned:
        return ""

    flat = re.sub(r"\s+", " ", cleaned)

    # 1) 直接抓规范句（比「1 范围」更稳，很多文档范围标题被拆散）
    normative_hits = _NORMATIVE_SENTENCE_RE.findall(flat)
    if normative_hits:
        # 合并连续的规定了 + 适用于
        chunks: list[str] = []
        for sent in normative_hits[:4]:
            sent = clean_display_text(sent, preserve_paragraphs=False)
            if len(sent) >= 12 and not _is_boilerplate_line(sent):
                chunks.append(sent if sent.endswith(("。", "！", "？", "；")) else sent + "。")
            if sum(len(x) for x in chunks) >= max_len:
                break
        if chunks:
            return _truncate("".join(chunks), max_len)

    # 2) 「范围」章节
    scope_match = _SCOPE_SECTION_RE.search(flat)
    if scope_match:
        scope = clean_display_text(scope_match.group(1), preserve_paragraphs=False)
        if len(scope) >= 16 and not _is_toc_like_text(scope):
            return _truncate(scope, max_len)

    # 3) 前言实质句
    preface_match = _PREFACE_SECTION_RE.search(cleaned)
    if preface_match:
        for sentence in re.split(r"[。！？；]", preface_match.group(1)):
            sentence = clean_display_text(sentence, preserve_paragraphs=False)
            if len(sentence) >= 16 and not _is_boilerplate_line(sentence) and not _is_toc_like_text(sentence):
                return _truncate(sentence + "。", max_len)

    # 4) 逐行挑选，强力跳过封面/目次/章节标题
    section_heads = {
        "范围",
        "规范性引用文件",
        "术语和定义",
        "缩略语",
        "引言",
        "前言",
        "目次",
        "参考文献",
    }
    picked: list[str] = []
    for line in cleaned.splitlines():
        line = clean_display_text(line, preserve_paragraphs=False)
        if _is_boilerplate_line(line) or _is_toc_like_text(line):
            continue
        if line.startswith("ICS") or re.match(r"^GB/?T?\s*[\d.]+", line, re.I):
            continue
        if line.rstrip("：:") in section_heads:
            continue
        # 跳过纯英文题名行
        if len(re.findall(r"[A-Za-z]", line)) >= 8 and len(re.findall(r"[\u4e00-\u9fff]", line)) < 2:
            continue
        picked.append(line)
        joined = " ".join(picked)
        if len(joined) >= max_len:
            joined = _truncate(joined, max_len)
            if not _is_toc_like_text(joined):
                return joined
            picked = []
            continue

    joined = clean_display_text(" ".join(picked), preserve_paragraphs=False)
    if (
        joined
        and not _is_toc_like_text(joined)
        and len(joined) >= 16
        and re.search(r"(规定了|适用于|确立了|界定了|本文件是|本标准是)", joined)
    ):
        return _truncate(joined, max_len)

    # 文本往往只有封面/目次（OCR 限页）时，不要把目录当描述
    return ""


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
