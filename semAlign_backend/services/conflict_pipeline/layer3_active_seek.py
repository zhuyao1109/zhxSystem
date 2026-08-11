"""第三层：主动信息探寻 — 低置信度时查废止/替代库并追踪引用链。

当第二层置信度不足时，检索标准废止/替代关系与引用链信息，
为冲突项补充 layer3_enrichment 字段供裁决层加权。
"""

from __future__ import annotations

import re
from typing import Any

from .models import CandidatePair, Layer2Result, Layer3Result

_REPLACEMENT_HINTS = ("替代", "代替", "废止", "作废", "被代替", "replaced", "superseded")
_STANDARD_NO_PARTS = (
    r"GB/?T\s*[\d.]+(?:\s*[-—]\s*\d{4})?",
    r"ISO\s*[\d.:]+",
)
_STANDARD_NO = re.compile(
    r"(?:{})".format("|".join(_STANDARD_NO_PARTS)),
    re.I,
)


_ABOLISHED_STATUSES = frozenset({"失效", "废止", "作废"})


def _hits_from_meta(
    label: str,
    meta: dict[str, Any],
    lookup: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """函数内部辅助：hits from meta。"""
    abolition_hits: list[dict[str, Any]] = []
    replacement_hits: list[dict[str, Any]] = []
    std_no = str(meta.get("standard_no") or "")
    record = lookup(std_no)
    if not record:
        return abolition_hits, replacement_hits
    status = str(record.get("status") or "")
    desc = str(record.get("description") or "")
    if status in _ABOLISHED_STATUSES:
        abolition_hits.append(
            {
                "side": label,
                "standard_no": std_no,
                "status": status,
                "note": "标准状态为失效/废止",
            }
        )
    if any(h in desc for h in _REPLACEMENT_HINTS):
        replacement_hits.append(
            {
                "side": label,
                "standard_no": std_no,
                "status": status,
                "description_excerpt": desc[:200],
                "note": "描述中包含替代/废止线索",
            }
        )
    return abolition_hits, replacement_hits


class StandardReplacementRegistry:
    """标准废止/替代库（基于 standards 目录 + 描述启发）。"""

    def __init__(self, catalog: list[dict[str, Any]] | None = None):
        """函数内部辅助：init  。"""
        self.catalog = catalog or []
        self._by_no = {
            re.sub(r"\s+", "", str(item.get("standard_no") or "").upper()): item
            for item in self.catalog
            if item.get("standard_no")
        }

    def lookup(self, standard_no: str) -> dict[str, Any]:
        """函数：lookup。"""
        key = re.sub(r"\s+", "", (standard_no or "").upper())
        return self._by_no.get(key, {})

    def _collect_meta_hits(
        self,
        meta_a: dict[str, Any],
        meta_b: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """函数内部辅助：collect meta hits。"""
        abolition_hits: list[dict[str, Any]] = []
        replacement_hits: list[dict[str, Any]] = []
        for label, meta in (("A", meta_a), ("B", meta_b)):
            side_abolition, side_replacement = _hits_from_meta(label, meta, self.lookup)
            abolition_hits.extend(side_abolition)
            replacement_hits.extend(side_replacement)
        return abolition_hits, replacement_hits

    def _collect_abolished_reference_hits(
        self,
        pair: CandidatePair,
        abolition_hits: list[dict[str, Any]],
    ) -> None:
        """函数内部辅助：collect abolished reference hits。"""
        combined = f"{pair.a_text} {pair.b_text}"
        for match in _STANDARD_NO.findall(combined):
            ref = self.lookup(match)
            if not ref:
                continue
            status = str(ref.get("status") or "")
            if status in _ABOLISHED_STATUSES:
                abolition_hits.append(
                    {"referenced_standard": match, "status": status, "note": "引用标准已失效"}
                )

    def query_for_pair(
        self,
        pair: CandidatePair,
        meta_a: dict[str, Any],
        meta_b: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """函数：query for pair。"""
        abolition_hits, replacement_hits = self._collect_meta_hits(meta_a, meta_b)
        self._collect_abolished_reference_hits(pair, abolition_hits)
        return abolition_hits, replacement_hits


class CitationChainTracker:
    """动态追踪引用链（同批标准目录内）。"""

    def __init__(self, catalog: list[dict[str, Any]] | None = None):
        """函数内部辅助：init  。"""
        self.catalog = catalog or []

    def _find_related_links(self, ref: str, normalized: str) -> list[dict[str, Any]]:
        """函数内部辅助：find related links。"""
        ref_key = ref.upper().replace(" ", "")
        links: list[dict[str, Any]] = []
        for item in self.catalog:
            other_no = re.sub(r"\s+", "", str(item.get("standard_no") or "").upper())
            if not other_no or other_no == normalized:
                continue
            desc = str(item.get("description") or "") + str(item.get("name") or "")
            if ref_key in desc.upper().replace(" ", ""):
                links.append(
                    {
                        "related_standard_no": item.get("standard_no"),
                        "name": item.get("name"),
                        "status": item.get("status"),
                    }
                )
        return links

    def _build_chain_node(self, ref: str) -> dict[str, Any]:
        """函数内部辅助：build chain node。"""
        normalized = re.sub(r"\s+", "", ref.upper())
        return {
            "standard_no": ref,
            "depth": 0,
            "links": self._find_related_links(ref, normalized),
        }

    def trace(self, pair: CandidatePair, max_depth: int = 3) -> list[dict[str, Any]]:
        """函数：trace。"""
        chain: list[dict[str, Any]] = []
        refs = set(_STANDARD_NO.findall(f"{pair.a_text} {pair.b_text}"))
        visited: set[str] = set()

        for ref in sorted(refs):
            normalized = re.sub(r"\s+", "", ref.upper())
            if normalized in visited:
                continue
            visited.add(normalized)
            node = self._build_chain_node(ref)
            if node["links"]:
                chain.append(node)
            if len(chain) >= max_depth:
                break
        return chain


def run_layer3(
    analyzed: list[tuple[CandidatePair, Layer2Result]],
    meta_a: dict[str, Any],
    meta_b: dict[str, Any],
    *,
    standards_catalog: list[dict[str, Any]] | None = None,
    enabled: bool = True,
) -> dict[tuple[int, int], Layer3Result]:
    """仅对低置信度候选对执行第三层。"""
    if not enabled:
        return {}

    registry = StandardReplacementRegistry(standards_catalog)
    tracker = CitationChainTracker(standards_catalog)
    out: dict[tuple[int, int], Layer3Result] = {}

    for pair, layer2 in analyzed:
        if not layer2.is_low_confidence:
            continue
        key = (pair.a_idx, pair.b_idx)
        abolition, replacement = registry.query_for_pair(pair, meta_a, meta_b)
        chain = tracker.trace(pair)
        notes_parts = []
        if abolition:
            notes_parts.append(f"发现 {len(abolition)} 条废止线索")
        if replacement:
            notes_parts.append(f"发现 {len(replacement)} 条替代线索")
        if chain:
            notes_parts.append(f"引用链节点 {len(chain)} 个")

        out[key] = Layer3Result(
            triggered=True,
            abolition_hits=abolition,
            replacement_hits=replacement,
            citation_chain=chain,
            notes="；".join(notes_parts) or "已执行主动探寻，未发现额外线索",
        )
    return out
