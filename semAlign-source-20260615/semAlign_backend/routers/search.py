"""智能检索路由 - 处理标准搜索和建议。"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.config import settings
from core.deps import get_db, get_current_user
from models.standard import Standard
from models.user import User
from schemas.base import APIResponse
from schemas.search import SearchResponse, SearchResult, SearchSuggestion
from utils.document_processor import get_chunk_store

router = APIRouter(prefix="/search", tags=["智能检索"])
logger = logging.getLogger(__name__)


def _run_optional_rag(keyword: str) -> tuple[str, list[str]]:
    """可选 RAG 开关：默认关闭，开启时失败也不影响主流程。"""
    if not settings.search_rag_enabled:
        return "", []
    try:
        from utils.rag import rag_query  # 惰性导入，避免未安装依赖时启动失败

        rag_top_k = max(1, int(settings.search_rag_top_k))
        rag = rag_query(keyword, top_k=rag_top_k)
        answer = str(rag.get("answer") or "").strip()
        sources = [str(x).strip() for x in (rag.get("sources") or []) if str(x).strip()]
        # 去重保序
        dedup_sources: list[str] = []
        seen: set[str] = set()
        for item in sources:
            if item in seen:
                continue
            seen.add(item)
            dedup_sources.append(item)
        return answer, dedup_sources
    except Exception as exc:
        logger.warning("RAG 开关已启用，但调用失败，已回退普通检索: %s", exc)
        return "", []


def _metadata_score(standard: Standard, keyword: str) -> float:
    keyword_lower = keyword.lower()
    score = 0.35
    if keyword_lower in (standard.standard_no or "").lower():
        score = max(score, 0.95)
    if keyword_lower in (standard.name or "").lower():
        score = max(score, 0.88)
    if keyword_lower in (standard.description or "").lower():
        score = max(score, 0.72)
    return min(score, 1.0)


def _snippet(text: str | None, keyword: str) -> str | None:
    if not text:
        return None
    normalized = " ".join(text.split())
    if not normalized:
        return None
    idx = normalized.lower().find(keyword.lower())
    if idx < 0:
        return normalized[:180]
    start = max(0, idx - 50)
    end = min(len(normalized), idx + 130)
    return normalized[start:end]


def _to_result(
    standard: Standard,
    relevance_score: float,
    match_type: str,
    excerpt: str | None = None,
) -> SearchResult:
    return SearchResult(
        id=standard.id,
        standard_no=standard.standard_no,
        name=standard.name,
        version=standard.version,
        status=standard.status,
        category=standard.category,
        department=standard.department,
        source_file=standard.source_file,
        relevance_score=max(0.0, min(relevance_score, 1.0)),
        match_type=match_type,
        match_excerpt=excerpt,
    )


def _vector_only_result(
    pseudo_id: int,
    source_name: str,
    relevance_score: float,
    excerpt: str | None = None,
    standard_no: str | None = None,
    display_name: str | None = None,
) -> SearchResult:
    base = Path(source_name).name if source_name else "未命名文档"
    return SearchResult(
        id=pseudo_id,
        standard_no=(standard_no or "").strip() or f"VECTOR::{base}",
        name=(display_name or "").strip() or base,
        version="-",
        status="向量库文档",
        category="临时索引",
        department=None,
        source_file=source_name or base,
        relevance_score=max(0.0, min(relevance_score, 1.0)),
        match_type="vector",
        match_excerpt=excerpt,
    )


def _vector_metadata_rows(keyword: str, limit: int = 20) -> list[tuple[str, int]]:
    project_root = Path(__file__).resolve().parents[1]
    chroma_dir = Path(settings.chroma_db_dir)
    if not chroma_dir.is_absolute():
        chroma_dir = (project_root / chroma_dir).resolve()
    db_path = chroma_dir / "chroma.sqlite3"
    if not db_path.exists():
        return []
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        rows = cur.execute(
            """
            select string_value as source_name, count(*) as chunk_count
            from embedding_metadata
            where key in ('source', 'source_file')
              and string_value like ?
            group by string_value
            order by chunk_count desc, source_name asc
            limit ?
            """,
            (f"%{keyword}%", limit),
        ).fetchall()
        return [(str(r[0]), int(r[1])) for r in rows if r and r[0]]
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def _push_suggestion(
    target: dict[tuple[str, str], SearchSuggestion],
    *,
    type_: str,
    text: str | None,
    delta: int = 1,
) -> None:
    value = (text or "").strip()
    if not value:
        return
    key = (type_, value.lower())
    existing = target.get(key)
    if existing is None:
        target[key] = SearchSuggestion(type=type_, text=value, count=max(1, int(delta)))
        return
    existing.count += max(1, int(delta))


def _find_standard_by_source(db: Session, source_name: str) -> Standard | None:
    source_base = Path(source_name).name
    return (
        db.query(Standard)
        .filter(
            or_(
                Standard.source_file == source_name,
                Standard.source_file == source_base,
                Standard.source_file.contains(source_name),
                Standard.source_file.contains(source_base),
            )
        )
        .first()
    )


def _score_from_chunk_count(chunk_count: int) -> float:
    return min(0.99, 0.88 + min(chunk_count, 50) * 0.001)


def _merge_standard_hit(
    result_map: Dict[int, SearchResult],
    standard: Standard,
    score: float,
    *,
    source_name: str | None = None,
    excerpt: str | None = None,
    match_type: str = "vector",
) -> None:
    if standard.id in result_map:
        merged = result_map[standard.id]
        merged.relevance_score = max(merged.relevance_score, score)
        merged.match_type = "hybrid"
        if source_name:
            merged.source_file = merged.source_file or source_name
        if excerpt:
            merged.match_excerpt = merged.match_excerpt or excerpt
        return
    result_map[standard.id] = _to_result(
        standard,
        relevance_score=score,
        match_type=match_type,
        excerpt=excerpt,
    )


def _add_or_bump_pseudo_result(
    result_map: Dict[int, SearchResult],
    key: str,
    score: float,
    *,
    source_name: str,
    excerpt: str | None = None,
    standard_no: str | None = None,
    display_name: str | None = None,
) -> None:
    pseudo_id = -abs(hash(key)) % 10_000_000 - 1
    existing = result_map.get(pseudo_id)
    if existing:
        existing.relevance_score = max(existing.relevance_score, score)
        if excerpt:
            existing.match_excerpt = existing.match_excerpt or excerpt
        return
    result_map[pseudo_id] = _vector_only_result(
        pseudo_id=pseudo_id,
        source_name=source_name,
        relevance_score=score,
        excerpt=excerpt,
        standard_no=standard_no,
        display_name=display_name,
    )


def _apply_direct_vector_rows(
    db: Session,
    result_map: Dict[int, SearchResult],
    keyword: str,
) -> None:
    for source_name, chunk_count in _vector_metadata_rows(keyword, limit=20):
        standard = _find_standard_by_source(db, source_name)
        score = _score_from_chunk_count(chunk_count)
        excerpt = f"命中文件来源：{Path(source_name).name}（{chunk_count} 个 chunk）"
        if standard is not None:
            _merge_standard_hit(
                result_map,
                standard,
                score,
                source_name=source_name,
                excerpt=excerpt,
            )
            continue
        _add_or_bump_pseudo_result(
            result_map,
            source_name,
            score,
            source_name=source_name,
            excerpt=excerpt,
        )


def _resolve_standard_from_meta(db: Session, meta: dict) -> Standard | None:
    standard_id = meta.get("standard_id")
    if standard_id is not None:
        found = db.query(Standard).filter(Standard.id == int(standard_id)).first()
        if found is not None:
            return found

    file_id = str(meta.get("file_id") or "").strip()
    if file_id.startswith("standard:"):
        try:
            sid = int(file_id.split(":", 1)[1])
            found = db.query(Standard).filter(Standard.id == sid).first()
            if found is not None:
                return found
        except (TypeError, ValueError):
            pass

    standard_no = meta.get("standard_no")
    if standard_no:
        found = db.query(Standard).filter(Standard.standard_no == str(standard_no)).first()
        if found is not None:
            return found

    source_name = str(meta.get("source_file") or meta.get("source") or "").strip()
    if source_name:
        return _find_standard_by_source(db, source_name)
    return None


def _apply_chunk_store_hits(
    db: Session,
    result_map: Dict[int, SearchResult],
    keyword: str,
) -> None:
    chunk_store = get_chunk_store()
    if chunk_store is None:
        return

    vector_hits = chunk_store.retrieve(keyword, top_k=8)
    for rank, hit in enumerate(vector_hits):
        meta = hit.get("metadata") or {}
        vector_score = max(0.45, 0.86 - rank * 0.07)
        excerpt = _snippet(hit.get("page_content"), keyword)
        standard = _resolve_standard_from_meta(db, meta)

        if standard is None:
            source_name = str(meta.get("source_file") or meta.get("source") or "").strip()
            std_no = str(meta.get("standard_no") or "").strip() or None
            std_name = str(meta.get("name") or "").strip() or None
            key = source_name or std_no or f"vector-hit-{rank}"
            _add_or_bump_pseudo_result(
                result_map,
                key,
                vector_score,
                source_name=source_name or (std_name or "向量库文档"),
                excerpt=excerpt,
                standard_no=std_no,
                display_name=std_name,
            )
            continue

        _merge_standard_hit(
            result_map,
            standard,
            vector_score,
            source_name=str(meta.get("source_file") or meta.get("source") or "") or None,
            excerpt=excerpt,
            match_type="vector",
        )


def _collect_standard_suggestions(
    row: Standard,
    needle_lower: str,
    suggestion_map: dict[tuple[str, str], SearchSuggestion],
) -> None:
    """从单条标准记录提取搜索建议。"""
    for type_, value, delta in (
        ("standard_no", row.standard_no, 3),
        ("name", row.name, 2),
        ("category", row.category, 1),
        ("department", row.department, 1),
    ):
        if value and needle_lower in value.lower():
            _push_suggestion(suggestion_map, type_=type_, text=value, delta=delta)


@router.get("", response_model=APIResponse[SearchResponse])
async def search_standards(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Standard).filter(
        or_(
            Standard.standard_no.contains(keyword),
            Standard.name.contains(keyword),
            Standard.description.contains(keyword),
            Standard.source_file.contains(keyword),
        )
    )
    metadata_hits = query.all()
    result_map: Dict[int, SearchResult] = {
        item.id: _to_result(
            item,
            relevance_score=_metadata_score(item, keyword),
            match_type="metadata",
            excerpt=_snippet(item.description, keyword),
        )
        for item in metadata_hits
    }

    _apply_direct_vector_rows(db, result_map, keyword)
    _apply_chunk_store_hits(db, result_map, keyword)

    results = sorted(result_map.values(), key=lambda item: item.relevance_score, reverse=True)
    rag_answer, rag_sources = _run_optional_rag(keyword)
    return APIResponse(
        data=SearchResponse(
            results=results,
            answer=rag_answer,
            sources=rag_sources,
            suggestions=[],
            total=len(results),
        )
    )


@router.get("/suggest", response_model=APIResponse[List[SearchSuggestion]])
async def get_search_suggestions(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    needle = keyword.strip()
    if not needle:
        return APIResponse(data=[])

    suggestion_map: dict[tuple[str, str], SearchSuggestion] = {}

    candidates = (
        db.query(Standard)
        .filter(
            or_(
                Standard.standard_no.contains(needle),
                Standard.name.contains(needle),
                Standard.category.contains(needle),
                Standard.department.contains(needle),
                Standard.source_file.contains(needle),
            )
        )
        .order_by(Standard.updated_at.desc())
        .limit(100)
        .all()
    )

    needle_lower = needle.lower()
    for row in candidates:
        _collect_standard_suggestions(row, needle_lower, suggestion_map)

    for source_name, chunk_count in _vector_metadata_rows(needle, limit=20):
        _push_suggestion(
            suggestion_map,
            type_="source_file",
            text=Path(source_name).name or source_name,
            delta=max(1, min(int(chunk_count), 50)),
        )

    type_priority = {
        "standard_no": 0,
        "name": 1,
        "category": 2,
        "department": 3,
        "source_file": 4,
    }
    suggestions = sorted(
        suggestion_map.values(),
        key=lambda item: (-item.count, type_priority.get(item.type, 99), item.text),
    )[:12]
    return APIResponse(data=suggestions)
