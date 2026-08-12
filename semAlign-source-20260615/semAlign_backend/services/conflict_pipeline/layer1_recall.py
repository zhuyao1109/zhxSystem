"""第一层：粗粒度候选冲突对召回 — 结构化索引 + 语义召回 + 引用关系扩展。"""

from __future__ import annotations

import re
from typing import Any

from .models import CandidatePair, ClauseRecord

_CITATION_PARTS = (
    r"GB/?T\s*[\d.]+(?:\s*[-—]\s*\d{4})?",
    r"ISO\s*[\d.:]+",
    r"IEC\s*[\d]+",
    r"IATA",
    r"ICAO",
)
_CITATION_PATTERN = re.compile(
    r"(?:{})".format("|".join(_CITATION_PARTS)),
    re.IGNORECASE,
)


def extract_citations(text: str) -> list[str]:
    hits = _CITATION_PATTERN.findall(text or "")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in hits:
        key = re.sub(r"\s+", "", item.upper())
        if key and key not in seen:
            seen.add(key)
            normalized.append(key)
    return normalized


def build_structured_index(clauses: list[ClauseRecord]) -> dict[str, Any]:
    """文档解析后的结构化索引（条款 + 引用倒排）。"""
    citation_index: dict[str, list[int]] = {}
    for clause in clauses:
        clause.citations = extract_citations(clause.text)
        for cite in clause.citations:
            citation_index.setdefault(cite, []).append(clause.idx)
    return {
        "clause_count": len(clauses),
        "citation_index": citation_index,
        "sections": sorted({c.section for c in clauses}),
    }


def _find_clause_by_idx(clauses: list[ClauseRecord], idx: int) -> ClauseRecord | None:
    return next((c for c in clauses if c.idx == idx), None)


def _make_citation_pair(
    ai: int,
    bi: int,
    ca: ClauseRecord,
    cb: ClauseRecord,
    cite: str,
    boost: float,
) -> CandidatePair:
    return CandidatePair(
        a_idx=ai,
        b_idx=bi,
        recall_score=boost,
        a_text=ca.text,
        b_text=cb.text,
        a_section=ca.section,
        b_section=cb.section,
        a_page=ca.page,
        b_page=cb.page,
        a_start_char=ca.start_char,
        b_start_char=cb.start_char,
        recall_sources=["citation_expansion", cite],
        match_type="citation",
    )


def _expand_citation_pairs_for_key(
    cite: str,
    cite_a: dict[str, list[int]],
    cite_b: dict[str, list[int]],
    clauses_a: list[ClauseRecord],
    clauses_b: list[ClauseRecord],
    existing: set[tuple[int, int]],
    expanded: list[CandidatePair],
    boost: float,
) -> None:
    for ai in cite_a.get(cite, [])[:5]:
        for bi in cite_b.get(cite, [])[:5]:
            if (ai, bi) in existing:
                continue
            ca = _find_clause_by_idx(clauses_a, ai)
            cb = _find_clause_by_idx(clauses_b, bi)
            if ca is None or cb is None:
                continue
            expanded.append(_make_citation_pair(ai, bi, ca, cb, cite, boost))
            existing.add((ai, bi))


def _expand_by_citations(
    pairs: list[CandidatePair],
    index_a: dict[str, Any],
    index_b: dict[str, Any],
    clauses_a: list[ClauseRecord],
    clauses_b: list[ClauseRecord],
    boost: float = 0.08,
) -> list[CandidatePair]:
    """引用关系扩展：共享引用标准的条款对提升召回分。"""
    cite_a: dict[str, list[int]] = index_a.get("citation_index") or {}
    cite_b: dict[str, list[int]] = index_b.get("citation_index") or {}
    shared_cites = set(cite_a.keys()) & set(cite_b.keys())
    if not shared_cites:
        return pairs

    existing = {(p.a_idx, p.b_idx) for p in pairs}
    expanded = list(pairs)
    for cite in shared_cites:
        _expand_citation_pairs_for_key(
            cite, cite_a, cite_b, clauses_a, clauses_b, existing, expanded, boost
        )
    return expanded


def recall_candidate_pairs(
    clauses_a: list[ClauseRecord],
    clauses_b: list[ClauseRecord],
    align_fn: Any,
    sim_threshold: float,
    *,
    enable_citation_expansion: bool = True,
    max_pairs: int = 120,
) -> tuple[list[CandidatePair], dict[str, Any]]:
    """
    语义相似召回 + 可选引用扩展。
    align_fn: (clauses_a, clauses_b, threshold) -> list[dict] 与 alignment_executor 对齐接口一致。
    """
    index_a = build_structured_index(clauses_a)
    index_b = build_structured_index(clauses_b)

    raw_pairs = align_fn(clauses_a, clauses_b, sim_threshold)
    candidates: list[CandidatePair] = []
    for p in raw_pairs:
        sources = ["semantic_similarity"]
        if p.get("match_type") == "citation":
            sources.append("citation")
        candidates.append(
            CandidatePair(
                a_idx=int(p.get("a_idx", 0)),
                b_idx=int(p.get("b_idx", 0)),
                recall_score=float(p.get("score", 0.0)),
                a_text=str(p.get("a_text") or ""),
                b_text=str(p.get("b_text") or ""),
                a_section=str(p.get("a_section") or "正文"),
                b_section=str(p.get("b_section") or "正文"),
                a_page=p.get("a_page"),
                b_page=p.get("b_page"),
                a_start_char=p.get("a_start_char"),
                b_start_char=p.get("b_start_char"),
                recall_sources=sources,
                match_type=str(p.get("match_type") or "semantic"),
            )
        )

    if enable_citation_expansion:
        candidates = _expand_by_citations(candidates, index_a, index_b, clauses_a, clauses_b)

    candidates.sort(key=lambda x: x.recall_score, reverse=True)
    candidates = candidates[:max_pairs]

    meta = {
        "layer": 1,
        "index_a": {"clause_count": index_a["clause_count"], "citation_keys": len(index_a["citation_index"])},
        "index_b": {"clause_count": index_b["clause_count"], "citation_keys": len(index_b["citation_index"])},
        "candidate_pair_count": len(candidates),
        "citation_expansion_enabled": enable_citation_expansion,
    }
    return candidates, meta
