"""标准对齐执行器 - 生产化版本（文本有效性+口径修正+ClauseAligner接入）。

职责：
    多源加载标准正文，切分条款并调用四层冲突识别流水线；
    可用时优先使用 ClauseAligner 进行语义配对，否则回退相似度矩阵。

数据加载优先级：
    1. standards.description 字段；
    2. data/texts 落盘解析文本；
    3. ChunkStore / Chroma sqlite 中的 chunk 拼接。

入口：
    run_alignment() — 由 alignment 路由在后台线程调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
import re
import sqlite3
from typing import Any

from core.config import settings
from utils.document_processor import DocumentProcessor, get_chunk_store
from services.conflict_pipeline import run_four_layer_pipeline
from services.conflict_pipeline.models import ClauseRecord

try:
    from services.conflict_detection.clause_aligner import ClauseAligner

    _ALIGNER_AVAILABLE = True
except Exception:
    ClauseAligner = None  # type: ignore
    _ALIGNER_AVAILABLE = False


# ---------------------------------------------------------------------------
# 内部数据结构
# ---------------------------------------------------------------------------

@dataclass
class _Clause:
    """内部条款数据结构，承载索引、正文、章节与页码。"""
    idx: int
    text: str
    section: str
    page: int | None = None
    start_char: int | None = None


# ---------------------------------------------------------------------------
# 路径解析与文本规范化
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """压缩连续空白并去除首尾空格，统一文本口径。"""
    return re.sub(r"\s+", " ", text or "").strip()


def _chroma_db_path() -> Path:
    """解析 Chroma 持久化 sqlite 路径（支持相对配置）。"""
    project_root = Path(__file__).resolve().parents[1]
    chroma_dir = Path(settings.chroma_db_dir)
    if not chroma_dir.is_absolute():
        chroma_dir = (project_root / chroma_dir).resolve()
    return chroma_dir / "chroma.sqlite3"


def _text_output_dir() -> Path:
    """解析标准解析文本输出目录。"""
    text_dir = Path(settings.text_output_dir)
    if not text_dir.is_absolute():
        text_dir = (Path(__file__).resolve().parents[1] / text_dir).resolve()
    return text_dir


def _is_effective_text(candidate: str) -> bool:
    """判断候选正文是否达到最小有效长度（120 字符）。"""
    return len(_clean_text(candidate)) >= 120


def _join_chunk_texts(items: list[dict[str, Any]]) -> str:
    """将向量 chunk 列表拼接为连续正文。"""
    return "\n".join(str(item.get("page_content") or "") for item in items if item.get("page_content"))


def _load_chunks_from_store(
    chunk_store: Any,
    *,
    sid: Any,
    file_id: str | None,
    source_file: str | None,
    source_base: str | None,
) -> list[dict[str, Any]]:
    """按 file_id / standard_id / source 多键查询 ChunkStore。"""
    lookups = []
    if file_id:
        lookups.append({"file_id": file_id})
    if sid is not None:
        lookups.append({"standard_id": sid})
    for key in ("source", "source_file"):
        if source_file:
            lookups.append({key: source_file})
        if source_base:
            lookups.append({key: source_base})
    for meta in lookups:
        rows = chunk_store.list_chunks(meta, limit=1000)
        if rows:
            return rows
    return []


# ---------------------------------------------------------------------------
# Chroma sqlite 与落盘文本加载
# ---------------------------------------------------------------------------

def _load_from_chroma_sqlite(
    *,
    sid: Any,
    file_id: str | None,
    source_file: str | None,
    source_base: str | None,
) -> list[str]:
    """直接从 Chroma sqlite 元数据表读取 chunk 文本。"""
    db_path = _chroma_db_path()
    if not db_path.exists():
        return []

    queries: list[tuple[str, tuple[Any, ...]]] = []
    if file_id:
        queries.append(
            (
                """
                select d.string_value
                from embedding_metadata s
                join embedding_metadata d on d.id = s.id
                where s.key='file_id' and s.string_value=?
                  and d.key='chroma:document'
                """,
                (file_id,),
            )
        )
    if sid is not None:
        queries.append(
            (
                """
                select d.string_value
                from embedding_metadata s
                join embedding_metadata d on d.id = s.id
                where s.key='standard_id' and s.int_value=?
                  and d.key='chroma:document'
                """,
                (int(sid),),
            )
        )
    for value in (source_file, source_base):
        if not value:
            continue
        queries.append(
            (
                """
                select d.string_value
                from embedding_metadata s
                join embedding_metadata d on d.id = s.id
                where s.key in ('source','source_file') and s.string_value=?
                  and d.key='chroma:document'
                """,
                (value,),
            )
        )

    conn: sqlite3.Connection | None = None
    candidates: list[str] = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for sql, params in queries:
            rows = cur.execute(sql, params).fetchall()
            chunks = [str(r[0]) for r in rows if r and r[0]]
            if chunks:
                candidates.append("\n".join(chunks))
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close()
    return candidates


# ---------------------------------------------------------------------------
# 页码标记与条款切分
# ---------------------------------------------------------------------------

def _load_text_by_suffix(source_file: str) -> str:
    """按源文件名后缀在 texts 目录中查找最长匹配文本。"""
    text_dir = _text_output_dir()
    if not text_dir.exists():
        return ""
    stem = Path(source_file).stem
    suffix_name = f"_{stem}.txt"
    best = ""
    try:
        for path in text_dir.glob(f"*{suffix_name}"):
            content = path.read_text(encoding="utf-8", errors="ignore")
            if len(_clean_text(content)) > len(_clean_text(best)):
                best = content
    except Exception:
        return ""
    return best


def _load_text_by_standard_no(standard_no: str) -> str:
    """在 texts 目录中按标准号模糊匹配正文。"""
    text_dir = _text_output_dir()
    if not text_dir.exists():
        return ""
    normalized_target = standard_no.upper().replace(" ", "")
    best_text = ""
    try:
        for txt_path in text_dir.glob("*.txt"):
            content = txt_path.read_text(encoding="utf-8", errors="ignore")
            if not content:
                continue
            normalized_content = content.upper().replace(" ", "")
            if normalized_target in normalized_content and len(content) > len(best_text):
                best_text = content
    except Exception:
        return ""
    return best_text


def _collect_page_marks(normalized: str) -> list[tuple[int, int]]:
    """从正文中提取「第 N 页 / page N」页码标记位置。"""
    page_marks: list[tuple[int, int]] = []
    for match in re.finditer(r"(?:第\s*(\d+)\s*页|page\s*(\d+))", normalized, flags=re.IGNORECASE):
        page_no = int(match.group(1) or match.group(2))
        page_marks.append((match.start(), page_no))
    return page_marks


def _page_for_position(page_marks: list[tuple[int, int]], pos: int) -> int | None:
    """根据字符偏移量映射到最近页码。"""
    current: int | None = None
    for mark_pos, page_no in page_marks:
        if mark_pos <= pos:
            current = page_no
        else:
            break
    return current


def _split_raw_parts(normalized: str) -> list[tuple[int, str]]:
    """按条款编号或句号将正文切分为原始片段。"""
    starts = [m.start() for m in re.finditer(r"(?m)^\s*\d+(?:\.\d+){0,4}[\s、.．)]{1,2}\S", normalized)]
    raw_parts: list[tuple[int, str]] = []
    if len(starts) > 1:
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(normalized)
            raw_parts.append((start, normalized[start:end]))
        return raw_parts
    for match in re.finditer(r"[^\n\r。；!?]+[。；!?]?", normalized):
        raw_parts.append((match.start(), match.group(0)))
    return raw_parts


def _clause_from_part(
    start: int,
    part: str,
    page_marks: list[tuple[int, int]],
    seen: set[str],
    idx: int,
) -> _Clause | None:
    """将原始片段转换为带章节号的条款对象。"""
    candidate = _clean_text(part)
    if len(candidate) < 12:
        return None
    if len(candidate) > 520:
        candidate = candidate[:520]
    dedup_key = candidate[:120]
    if dedup_key in seen:
        return None
    seen.add(dedup_key)
    sec_match = re.match(r"^(\d+(?:\.\d+){0,4})[\s、.．)]", candidate)
    section = sec_match.group(1) if sec_match else "正文"
    return _Clause(
        idx=idx,
        text=candidate,
        section=section,
        page=_page_for_position(page_marks, start),
        start_char=start,
    )


# ---------------------------------------------------------------------------
# 相似度计算与条款配对（fallback）
# ---------------------------------------------------------------------------

def _split_clauses(text: str, max_count: int = 200) -> list[_Clause]:
    """将标准全文切分为有限数量的对齐条款单元。"""
    if not text.strip():
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    page_marks = _collect_page_marks(normalized)
    raw_parts = _split_raw_parts(normalized)

    clauses: list[_Clause] = []
    seen: set[str] = set()
    for start, part in raw_parts:
        clause = _clause_from_part(start, part, page_marks, seen, len(clauses))
        if clause is None:
            continue
        clauses.append(clause)
        if len(clauses) >= max_count:
            break
    return clauses


def _tokenize(text: str) -> set[str]:
    """简易分词：提取中英文与数字 token 集合。"""
    return {tok for tok in re.split(r"[^\w\u4e00-\u9fff]+", (text or "").lower()) if len(tok) >= 2}


def _fallback_similarity(a: str, b: str) -> float:
    """Jaccard + SequenceMatcher 混合相似度（Aligner 不可用时的回退）。"""
    if not a or not b:
        return 0.0
    seq_score = SequenceMatcher(None, a, b).ratio()
    ta = _tokenize(a)
    tb = _tokenize(b)
    token_score = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    return round(seq_score * 0.6 + token_score * 0.4, 4)


def _try_load_from_chunk_store(
    _standard: Any,
    *,
    sid: Any,
    file_id: str | None,
    source_file: str | None,
    source_base: str | None,
) -> str | None:
    """尝试从 ChunkStore 加载标准关联 chunk 文本。"""
    chunk_store = get_chunk_store()
    if chunk_store is None:
        return None
    by_meta = _load_chunks_from_store(
        chunk_store,
        sid=sid,
        file_id=file_id,
        source_file=source_file,
        source_base=source_base,
    )
    if not by_meta:
        return None
    return _join_chunk_texts(by_meta)


def _try_load_from_saved_files(_standard: Any, source_file: str | None) -> str | None:
    """尝试从 uploads/texts 落盘文件加载正文。"""
    if not source_file:
        return None
    processor = DocumentProcessor()
    saved = processor.load_saved_text(source_file)
    if saved and saved.strip():
        return saved
    suffix_text = _load_text_by_suffix(source_file)
    return suffix_text if suffix_text.strip() else None


def _collect_standard_text_candidates(standard: Any) -> list[str]:
    """汇总描述字段、文件、向量库等多源正文候选。"""
    sid = getattr(standard, "id", None)
    file_id = f"standard:{sid}" if sid is not None else None
    source_file = getattr(standard, "source_file", None)
    source_base = Path(source_file).name if source_file else None
    candidates: list[str] = []

    chunk_text = _try_load_from_chunk_store(
        standard,
        sid=sid,
        file_id=file_id,
        source_file=source_file,
        source_base=source_base,
    )
    if chunk_text:
        candidates.append(chunk_text)

    for joined in _load_from_chroma_sqlite(
        sid=sid,
        file_id=file_id,
        source_file=source_file,
        source_base=source_base if source_base != source_file else None,
    ):
        candidates.append(joined)

    saved_text = _try_load_from_saved_files(standard, source_file)
    if saved_text:
        candidates.append(saved_text)

    standard_no = str(getattr(standard, "standard_no", "") or "").strip()
    if standard_no:
        matched = _load_text_by_standard_no(standard_no)
        if matched.strip():
            candidates.append(matched)

    fallback = "\n".join(
        x
        for x in [
            getattr(standard, "standard_no", "") or "",
            getattr(standard, "name", "") or "",
            getattr(standard, "description", "") or "",
        ]
        if x.strip()
    )
    if fallback:
        candidates.append(fallback)
    return candidates


# ---------------------------------------------------------------------------
# 标准正文汇总与有效性校验
# ---------------------------------------------------------------------------

def _load_standard_text(standard: Any) -> str:
    """选择最长有效候选作为标准对齐输入正文。"""
    candidates = _collect_standard_text_candidates(standard)
    for text in candidates:
        if _is_effective_text(text):
            return text
    return max(candidates, key=lambda x: len(_clean_text(x)), default="")


def _ensure_effective_text(text: str, label: str) -> None:
    """校验正文长度与条款数量，不满足则抛出 ValueError。"""
    normalized = _clean_text(text)
    if len(normalized) < 40:
        raise ValueError(f"{label} 未加载到有效正文（文本长度过短）")
    clauses = _split_clauses(normalized, max_count=20)
    if len(clauses) < 2:
        raise ValueError(f"{label} 未加载到足够条款（至少需要 2 条）")


def _severity(score: float) -> str:
    """按相似度分数映射冲突严重级别文案。"""
    if score < 0.45:
        return "高冲突"
    if score < 0.60:
        return "中冲突"
    return "低冲突"


def _extract_year(s: str | None) -> int | None:
    """从标准号字符串中提取四位年份。"""
    if not s:
        return None
    m = re.search(r"(19|20)\d{2}", s)
    return int(m.group(0)) if m else None


def _is_international(standard_no: str, name: str) -> bool:
    """根据标准号与名称判断是否国际/行业标准。"""
    text = f"{standard_no} {name}".lower()
    keywords = ("iso", "iec", "iata", "icao", "国际", "international")
    return any(k in text for k in keywords)


def _is_mandatory_standard(standard_no: str, status: str) -> bool:
    """根据标准号与状态判断是否强制性标准。"""
    text = f"{standard_no} {status}".lower()
    mandatory_hits = ("强制", "mandatory", "gb ")
    return any(k in text for k in mandatory_hits)


def _build_standard_meta(standard: Any) -> dict[str, Any]:
    """构建对齐流水线使用的标准元数据字典。"""
    standard_no = str(getattr(standard, "standard_no", "") or "")
    name = str(getattr(standard, "name", "") or "")
    status = str(getattr(standard, "status", "") or "")
    year = _extract_year(standard_no)
    publisher = "international" if _is_international(standard_no, name) else "domestic"
    std_type = "mandatory" if _is_mandatory_standard(standard_no, status) else "technical"
    return {
        "publisher": publisher,
        "publish_date": f"{year}-01-01" if year else "",
        "standard_type": std_type,
    }


# ---------------------------------------------------------------------------
# 优先级规则与解决方案生成
# ---------------------------------------------------------------------------

def _priority_config_from_selected(priority_rules: list[str]) -> dict[str, Any]:
    """将前端勾选的优先级规则转为 RuleOrchestrator 配置。"""
    enabled = set(priority_rules or [])
    return {
        "enabled_rules": {
            "international_priority": ("international" in enabled) or (not enabled),
            "latest_revision": ("latest" in enabled) or (not enabled),
            "mandatory_priority": ("mandatory" in enabled) or (not enabled),
        },
        "strategy": "weighted_sum",
        "weights": {
            "international_priority": 0.34,
            "latest_revision": 0.33,
            "mandatory_priority": 0.33,
        },
    }


def _priority_score(
    similarity_score: float,
    pair: dict[str, Any],
    selected_rules: list[str],
    eval_result: dict[str, Any],
) -> float:
    # 基础：越不相似优先级越高
    """综合相似度、置信度与规则标签计算优先级分数。"""
    score = (1.0 - similarity_score) * 100.0
    # 强制词冲突提升优先级
    text_a = pair.get("a_text", "")
    text_b = pair.get("b_text", "")
    mandatory_kw = ("必须", "应", "shall", "must", "required")
    if any(k in text_a for k in mandatory_kw) or any(k in text_b for k in mandatory_kw):
        score += 12.0
    # 内容丰富者规则：长度差异越大，优先级越高
    if "comprehensive" in selected_rules:
        score += min(abs(len(text_a) - len(text_b)) / 10.0, 12.0)
    # 规则引擎置信度加权
    conf = float(eval_result.get("confidence", 0.0) or 0.0)
    score += conf * 10.0
    return round(score, 2)


def _build_solution(conflict: dict[str, Any], idx: int) -> dict[str, Any]:
    """为单条冲突生成前端展示用的解决方案结构。"""
    severity = conflict.get("severity", "中冲突")
    s1 = (conflict.get("standard1") or {}).get("name", "标准1")
    s2 = (conflict.get("standard2") or {}).get("name", "标准2")
    return {
        "conflict_id": conflict["id"],
        "title": conflict["title"],
        "severity": severity,
        "description": f"建议统一 {s1} 与 {s2} 在该条款的术语定义和判定口径，并补充映射说明。",
        "reason": "基于语义相似度与术语差异自动生成，建议进入人工复核流程。",
        "creator": "系统自动建议",
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approve_count": 0,
        "reject_count": 0,
        "rank": idx + 1,
    }


# ---------------------------------------------------------------------------
# 条款对齐：ClauseAligner 与 fallback
# ---------------------------------------------------------------------------

def _append_aligned_pair(
    pairs: list[dict[str, Any]],
    ca: _Clause,
    cb: _Clause,
    score: float,
    *,
    match_type: str,
) -> dict[str, Any]:
    """构造单条对齐结果并追加到列表。"""
    item = {
        "a_idx": ca.idx,
        "b_idx": cb.idx,
        "score": score,
        "a_text": ca.text,
        "b_text": cb.text,
        "a_section": ca.section,
        "b_section": cb.section,
        "a_page": ca.page,
        "b_page": cb.page,
        "a_start_char": ca.start_char,
        "b_start_char": cb.start_char,
        "match_type": match_type,
    }
    pairs.append(item)
    return item


def _align_pairs_with_fallback(
    clauses_a: list[_Clause],
    clauses_b: list[_Clause],
    sim_threshold: float,
) -> list[dict[str, Any]]:
    """贪心配对条款；不足时按放宽阈值补全。"""
    used_b: set[int] = set()
    pairs: list[dict[str, Any]] = []

    def _collect(threshold: float, match_type: str) -> None:
        for ca in clauses_a:
            best_cb: _Clause | None = None
            best_score = 0.0
            for cb in clauses_b:
                if cb.idx in used_b:
                    continue
                score = _fallback_similarity(ca.text, cb.text)
                if score > best_score:
                    best_cb = cb
                    best_score = score
            if best_cb is None or best_score < threshold:
                continue
            used_b.add(best_cb.idx)
            _append_aligned_pair(pairs, ca, best_cb, best_score, match_type=match_type)

    _collect(sim_threshold, "fallback")
    min_expected = max(1, int(min(len(clauses_a), len(clauses_b)) * 0.3))
    if len(pairs) < min_expected:
        _collect(max(sim_threshold * 0.8, 0.12), "fallback_relaxed")
    return pairs


def _align_pairs_for_pipeline(
    clauses_a: list[ClauseRecord],
    clauses_b: list[ClauseRecord],
    sim_threshold: float,
) -> list[dict[str, Any]]:
    """供四层流水线调用的条款配对适配层。"""
    internal_a = [
        _Clause(idx=c.idx, text=c.text, section=c.section, page=c.page, start_char=c.start_char)
        for c in clauses_a
    ]
    internal_b = [
        _Clause(idx=c.idx, text=c.text, section=c.section, page=c.page, start_char=c.start_char)
        for c in clauses_b
    ]
    return _align_pairs(internal_a, internal_b, sim_threshold)


def _align_pairs(
    clauses_a: list[_Clause],
    clauses_b: list[_Clause],
    sim_threshold: float,
) -> list[dict[str, Any]]:
    """优先 ClauseAligner，失败时回退 fallback 配对。"""
    if _ALIGNER_AVAILABLE and ClauseAligner is not None:
        try:
            aligner = ClauseAligner(similarity_threshold=sim_threshold)
            pairs = aligner.align_clauses(
                [{"id": c.idx, "text": c.text, "section": c.section} for c in clauses_a],
                [{"id": c.idx, "text": c.text, "section": c.section} for c in clauses_b],
            )
            normalized: list[dict[str, Any]] = []
            for p in pairs:
                ca = p.get("clause_a") or {}
                cb = p.get("clause_b") or {}
                normalized.append(
                    {
                        "a_idx": int(ca.get("id", 0)),
                        "b_idx": int(cb.get("id", 0)),
                        "score": float(p.get("similarity_score", 0.0)),
                        "a_text": str(ca.get("text") or ""),
                        "b_text": str(cb.get("text") or ""),
                        "a_section": str(ca.get("section") or "正文"),
                        "b_section": str(cb.get("section") or "正文"),
                        "match_type": str(p.get("match_type") or "semantic"),
                    }
                )
            if normalized:
                return normalized
        except Exception:
            pass
    return _align_pairs_with_fallback(clauses_a, clauses_b, sim_threshold=sim_threshold)


# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------

def run_alignment(
    standard_a: Any,
    standard_b: Any,
    options: dict[str, Any] | None = None,
    standards_catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """对齐任务主入口：加载文本、切条款、执行四层流水线并返回结果 JSON。"""
    options = options or {}

    text_a = _load_standard_text(standard_a)
    text_b = _load_standard_text(standard_b)
    _ensure_effective_text(text_a, getattr(standard_a, "name", "标准组1"))
    _ensure_effective_text(text_b, getattr(standard_b, "name", "标准组2"))

    clauses_a = _split_clauses(text_a)
    clauses_b = _split_clauses(text_b)

    result = run_four_layer_pipeline(
        standard_a=standard_a,
        standard_b=standard_b,
        clauses_a=clauses_a,
        clauses_b=clauses_b,
        align_fn=_align_pairs_for_pipeline,
        build_meta_fn=_build_standard_meta,
        priority_config_fn=_priority_config_from_selected,
        options=options,
        standards_catalog=standards_catalog,
    )
    result.setdefault("meta", {})["aligner"] = "ClauseAligner" if _ALIGNER_AVAILABLE else "fallback"
    return result
