"""第四层：冲突裁决与输出生成 — 综合多智能体结果 + JSON + 自然语言报告。

输入第二层分析结果与第三层引用链 enrichment，输出带优先级排序的
冲突列表、解决方案建议及 Markdown 格式检测报告。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import AdjudicatedConflict, CandidatePair, Layer2Result, Layer3Result


def _severity(similarity: float, confidence: float) -> str:
    """结合相似度与冲突置信度映射严重级别。"""
    if similarity < 0.45 or confidence >= 0.75:
        return "高冲突"
    if similarity < 0.60 or confidence >= 0.55:
        return "中冲突"
    return "低冲突"


def _priority_score(
    similarity: float,
    confidence: float,
    authority: float,
    atomic_count: int,
    layer3: Layer3Result | None,
    selected_rules: list[str],
) -> float:
    """计算冲突项优先级综合分数。"""
    score = (1.0 - similarity) * 50.0 + confidence * 30.0 + authority * 20.0
    score += min(12.0, atomic_count * 3.0)
    if layer3 and layer3.triggered and (layer3.abolition_hits or layer3.replacement_hits):
        score += 8.0
    if "comprehensive" in selected_rules:
        score += 4.0
    return round(score, 2)


def _is_conflict_pair(sim: float, l2: Layer2Result, conflict_threshold: float) -> bool:
    """判断候选对是否应纳入冲突列表。"""
    return sim < conflict_threshold or (
        l2.atomic_differences and l2.conflict_confidence >= 0.5
    )


def _layer3_to_dict(l3: Layer3Result | None) -> dict[str, Any]:
    """将第三层结果序列化为 comparison API 兼容字典。"""
    return {
        "triggered": bool(l3 and l3.triggered),
        "abolition_hits": l3.abolition_hits if l3 else [],
        "replacement_hits": l3.replacement_hits if l3 else [],
        "citation_chain": l3.citation_chain if l3 else [],
        "notes": l3.notes if l3 else "",
    }


def _build_adjudication_summary(l2: Layer2Result, l3: Layer3Result | None) -> str:
    """生成冲突裁决自然语言摘要。"""
    atomic_summary = "；".join(
        d.get("description", "") for d in l2.atomic_differences[:3]
    ) or "语义相似度偏低"
    summary_parts = [
        f"冲突置信度 {l2.conflict_confidence:.2f}",
        f"权威性分数 {l2.authority_score:.2f}",
        atomic_summary,
    ]
    if l3 and l3.triggered:
        summary_parts.append(l3.notes)
    return "。".join(summary_parts)


def _build_adjudicated_conflict(
    pair: CandidatePair,
    l2: Layer2Result,
    l3: Layer3Result | None,
    *,
    conflict_idx: int,
    standard_a_name: str,
    standard_b_name: str,
    selected_rules: list[str],
) -> AdjudicatedConflict:
    """组装单条裁决后的冲突实体。"""
    sim = l2.similarity_score
    l3_dict = _layer3_to_dict(l3)
    p_score = _priority_score(
        sim,
        l2.conflict_confidence,
        l2.authority_score,
        len(l2.atomic_differences),
        l3,
        selected_rules,
    )
    return AdjudicatedConflict(
        id=f"conflict-{conflict_idx}",
        title=f"条款语义冲突 #{conflict_idx}",
        severity=_severity(sim, l2.conflict_confidence),
        similarity_score=round(sim, 4),
        conflict_confidence=l2.conflict_confidence,
        authority_score=l2.authority_score,
        standard1={"name": standard_a_name, "content": pair.a_text},
        standard2={"name": standard_b_name, "content": pair.b_text},
        location={
            "standard1_clause_index": pair.a_idx + 1,
            "standard2_clause_index": pair.b_idx + 1,
            "standard1_section": pair.a_section,
            "standard2_section": pair.b_section,
            "standard1_page": pair.a_page,
            "standard2_page": pair.b_page,
            "standard1_excerpt": pair.a_text[:120],
            "standard2_excerpt": pair.b_text[:120],
            "recall_sources": pair.recall_sources,
        },
        priority_score=p_score,
        priority_rank=0,
        priority_recommendation=l2.authority_recommendation,
        priority_confidence=l2.authority_score,
        priority_rule_details=l2.authority_rule_details,
        atomic_differences=l2.atomic_differences,
        layer3=l3_dict,
        adjudication_summary=_build_adjudication_summary(l2, l3),
    )


def adjudicate_conflicts(
    analyzed: list[tuple[CandidatePair, Layer2Result]],
    layer3_map: dict[tuple[int, int], Layer3Result],
    *,
    standard_a_name: str,
    standard_b_name: str,
    conflict_threshold: float,
    selected_rules: list[str],
    max_conflicts: int = 80,
) -> list[AdjudicatedConflict]:
    """第四层主流程：过滤、裁决、排序并限制最大冲突数。"""
    conflicts: list[AdjudicatedConflict] = []
    idx = 0

    for pair, l2 in analyzed:
        if not _is_conflict_pair(l2.similarity_score, l2, conflict_threshold):
            continue

        idx += 1
        l3 = layer3_map.get((pair.a_idx, pair.b_idx))
        conflicts.append(
            _build_adjudicated_conflict(
                pair,
                l2,
                l3,
                conflict_idx=idx,
                standard_a_name=standard_a_name,
                standard_b_name=standard_b_name,
                selected_rules=selected_rules,
            )
        )
        if len(conflicts) >= max_conflicts:
            break

    conflicts.sort(key=lambda c: (c.priority_score, c.conflict_confidence), reverse=True)
    for rank, item in enumerate(conflicts, start=1):
        item.priority_rank = rank
    return conflicts


def conflicts_to_legacy_dict(conflicts: list[AdjudicatedConflict]) -> list[dict[str, Any]]:
    """转换为前端 comparison API 兼容结构。"""
    out: list[dict[str, Any]] = []
    for c in conflicts:
        out.append(
            {
                "id": c.id,
                "title": c.title,
                "severity": c.severity,
                "similarity_score": c.similarity_score,
                "conflict_confidence": c.conflict_confidence,
                "authority_score": c.authority_score,
                "standard1": c.standard1,
                "standard2": c.standard2,
                "location": c.location,
                "priority_score": c.priority_score,
                "priority_rank": c.priority_rank,
                "priority_recommendation": c.priority_recommendation,
                "priority_confidence": c.priority_confidence,
                "priority_rule_details": c.priority_rule_details,
                "atomic_differences": c.atomic_differences,
                "layer3_enrichment": c.layer3,
                "adjudication_summary": c.adjudication_summary,
            }
        )
    return out


def build_solutions(conflicts: list[AdjudicatedConflict], limit: int = 15) -> list[dict[str, Any]]:
    """基于冲突列表生成解决建议条目。"""
    solutions: list[dict[str, Any]] = []
    for idx, c in enumerate(conflicts[:limit]):
        s1 = (c.standard1 or {}).get("name", "标准1")
        s2 = (c.standard2 or {}).get("name", "标准2")
        solutions.append(
            {
                "conflict_id": c.id,
                "title": c.title,
                "severity": c.severity,
                "description": (
                    f"建议统一 {s1} 与 {s2} 的术语与判定口径。"
                    f" 原子差异 {len(c.atomic_differences)} 项。"
                ),
                "reason": c.adjudication_summary,
                "creator": "四层冲突识别流水线",
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "approve_count": 0,
                "reject_count": 0,
                "rank": idx + 1,
            }
        )
    return solutions


def generate_natural_language_report(
    *,
    standard_group1: str,
    standard_group2: str,
    conflicts: list[AdjudicatedConflict],
    stats: dict[str, Any],
    pipeline_meta: dict[str, Any],
) -> str:
    """生成 Markdown 格式的冲突检测报告全文。"""
    lines = [
        "# 标准冲突检测报告",
        "",
        f"**比对对象**：{standard_group1}  vs  {standard_group2}",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**流水线版本**：{pipeline_meta.get('version', '4-layer-v1')}",
        "",
        "## 一、总体统计",
        f"- 冲突率：{stats.get('conflict_rate', 0)}%",
        f"- 高匹配率：{stats.get('match_rate', 0)}%",
        f"- 待处理率：{stats.get('pending_rate', 0)}%",
        f"- 检出冲突：{stats.get('conflict_count', 0)} 条",
        f"- 第二层低置信度触发第三层：{pipeline_meta.get('layer3_triggered_count', 0)} 对",
        "",
        "## 二、冲突摘要（按优先级）",
    ]
    for c in conflicts[:10]:
        lines.append(
            f"\n### {c.id}（{c.severity}，优先级 #{c.priority_rank}）\n"
            f"- 置信度：{c.conflict_confidence}，权威性：{c.authority_score}\n"
            f"- 建议：{c.priority_recommendation}\n"
            f"- 摘要：{c.adjudication_summary}\n"
        )
        if c.atomic_differences:
            lines.append("- 原子差异：")
            for d in c.atomic_differences[:3]:
                lines.append(f"  - [{d.get('dimension')}] {d.get('description')}")
        if c.layer3.get("triggered"):
            lines.append(f"- 主动探寻：{c.layer3.get('notes', '')}")

    lines.extend(
        [
            "",
            "## 三、处理建议",
            "1. 优先处理高冲突且置信度高的条目；",
            "2. 对第三层已补充废止/替代线索的条目，核对标准有效性；",
            "3. 人工复核后通过审核发布流程归档。",
        ]
    )
    return "\n".join(lines)
