"""四层标准冲突识别主流水线。

串联 layer1 召回 → layer2 智能体分析 → layer3 主动探寻 → layer4 裁决输出，
并调用 RuleOrchestrator 完成优先级融合，最终生成 comparison API 兼容结构。

调用方：
    alignment_executor.run_alignment() 在后台线程中执行本流水线。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from services.rule_engine.rule_orchestrator import RuleOrchestrator

from .layer1_recall import recall_candidate_pairs
from .layer2_agents import run_layer2
from .layer3_active_seek import run_layer3
from .layer4_adjudication import (
    adjudicate_conflicts,
    build_solutions,
    conflicts_to_legacy_dict,
    generate_natural_language_report,
)
from .models import ClauseRecord

PIPELINE_VERSION = "4-layer-v1"


def _to_clause_records(clauses: list[Any]) -> list[ClauseRecord]:
    """函数内部辅助：to clause records。"""
    out: list[ClauseRecord] = []
    for c in clauses:
        out.append(
            ClauseRecord(
                idx=int(getattr(c, "idx", 0)),
                text=str(getattr(c, "text", "")),
                section=str(getattr(c, "section", "正文")),
                page=getattr(c, "page", None),
                start_char=getattr(c, "start_char", None),
            )
        )
    return out


def run_four_layer_pipeline(
    *,
    standard_a: Any,
    standard_b: Any,
    clauses_a: list[Any],
    clauses_b: list[Any],
    align_fn: Callable[[list[ClauseRecord], list[ClauseRecord], float], list[dict[str, Any]]],
    build_meta_fn: Callable[[Any], dict[str, Any]],
    priority_config_fn: Callable[[list[str]], dict[str, Any]],
    options: dict[str, Any] | None = None,
    standards_catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """执行图例四层架构，返回与 alignment_executor 兼容的 result_json。"""
    options = options or {}
    sim_threshold = float(options.get("similarityThreshold", 0.42))
    conflict_threshold = float(options.get("conflictThreshold", 0.58))
    high_match_threshold = float(options.get("highMatchThreshold", 0.75))
    confidence_threshold = float(options.get("confidenceThreshold", 0.55))
    enable_layer3 = bool(options.get("enableLayer3", True))
    enable_citation_expansion = bool(options.get("enableCitationExpansion", True))

    priority_rules = options.get("priorityRules") or []
    if not isinstance(priority_rules, list):
        priority_rules = []
    selected_rules = [str(r) for r in priority_rules]

    records_a = _to_clause_records(clauses_a)
    records_b = _to_clause_records(clauses_b)
    meta_a = build_meta_fn(standard_a)
    meta_b = build_meta_fn(standard_b)
    meta_a["standard_no"] = str(getattr(standard_a, "standard_no", "") or "")
    meta_b["standard_no"] = str(getattr(standard_b, "standard_no", "") or "")

    name_a = getattr(standard_a, "name", "标准组1")
    name_b = getattr(standard_b, "name", "标准组2")

    # —— 第一层：粗召回 ——
    candidates, layer1_meta = recall_candidate_pairs(
        records_a,
        records_b,
        align_fn,
        sim_threshold,
        enable_citation_expansion=enable_citation_expansion,
    )

    # —— 第二层：多智能体 ——
    orchestrator = RuleOrchestrator(priority_config_fn(selected_rules))
    analyzed, layer2_meta = run_layer2(
        candidates,
        meta_a,
        meta_b,
        orchestrator,
        conflict_threshold=conflict_threshold,
        confidence_threshold=confidence_threshold,
    )

    # —— 第三层：低置信度主动探寻 ——
    layer3_map = run_layer3(
        analyzed,
        meta_a,
        meta_b,
        standards_catalog=standards_catalog,
        enabled=enable_layer3,
    )
    layer3_meta = {
        "layer": 3,
        "triggered_pair_count": len(layer3_map),
        "enabled": enable_layer3,
    }

    # —— 第四层：裁决与报告 ——
    adjudicated = adjudicate_conflicts(
        analyzed,
        layer3_map,
        standard_a_name=str(name_a),
        standard_b_name=str(name_b),
        conflict_threshold=conflict_threshold,
        selected_rules=selected_rules,
    )
    conflicts = conflicts_to_legacy_dict(adjudicated)

    matched_a_indices = {pair.a_idx for pair, _ in analyzed}
    matched_b_indices = {pair.b_idx for pair, _ in analyzed}
    # clusters from all analyzed pairs (up to 80)
    clusters: list[dict[str, Any]] = []
    for idx, (pair, l2) in enumerate(analyzed[:80]):
        is_conflict = l2.similarity_score < conflict_threshold or bool(l2.atomic_differences)
        title = pair.a_text[:20] + ("…" if len(pair.a_text) > 20 else "")
        clusters.append(
            {
                "title": title or f"语义簇 {idx + 1}",
                "clause_count": 2,
                "cluster_type": 1 if is_conflict else 2,
                "clauses": [
                    {"source": name_a, "content": pair.a_text, "is_conflict": is_conflict},
                    {"source": name_b, "content": pair.b_text, "is_conflict": is_conflict},
                ],
                "similarity_score": l2.similarity_score,
                "match_type": l2.match_type,
                "conflict_confidence": l2.conflict_confidence,
            }
        )

    unmatched_a = [c for c in records_a if c.idx not in matched_a_indices]
    unmatched_b = [c for c in records_b if c.idx not in matched_b_indices]

    total_basis = max(len(records_a), len(records_b), 1)
    conflict_count = len(conflicts)
    all_pairs_scores = [l2.similarity_score for _, l2 in analyzed]
    match_count = len([s for s in all_pairs_scores if s >= high_match_threshold])
    pending_count = max(total_basis - conflict_count - match_count, 0)

    stats = {
        "conflict_rate": int(round(conflict_count * 100 / total_basis)),
        "match_rate": int(round(match_count * 100 / total_basis)),
        "pending_rate": int(round(pending_count * 100 / total_basis)),
        "conflict_count": conflict_count,
        "match_count": match_count,
        "pending_count": pending_count,
        "matched_pair_count": len(analyzed),
        "unmatched_group1_count": len(unmatched_a),
        "unmatched_group2_count": len(unmatched_b),
    }

    pipeline_meta = {
        "version": PIPELINE_VERSION,
        "layers": [layer1_meta, layer2_meta, layer3_meta],
        "layer3_triggered_count": layer3_meta.get("triggered_pair_count", 0),
        "confidence_threshold": confidence_threshold,
    }

    report_text = generate_natural_language_report(
        standard_group1=f"{getattr(standard_a, 'standard_no', '')} {name_a}".strip(),
        standard_group2=f"{getattr(standard_b, 'standard_no', '')} {name_b}".strip(),
        conflicts=adjudicated,
        stats=stats,
        pipeline_meta=pipeline_meta,
    )

    solutions = build_solutions(adjudicated)

    return {
        "standard_group1": f"{getattr(standard_a, 'standard_no', '')} {name_a}".strip(),
        "standard_group2": f"{getattr(standard_b, 'standard_no', '')} {name_b}".strip(),
        "comparison_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alignment_mode": "四层冲突识别",
        "priority_rules": "，".join(selected_rules) or "默认规则",
        "status": "比对完成",
        "report_text": report_text,
        "stats": stats,
        "clusters": clusters,
        "conflicts": conflicts,
        "solutions": solutions,
        "unmatched": {
            "standard1": [
                {"index": item.idx + 1, "section": item.section, "content": item.text}
                for item in unmatched_a[:50]
            ],
            "standard2": [
                {"index": item.idx + 1, "section": item.section, "content": item.text}
                for item in unmatched_b[:50]
            ],
        },
        "meta": {
            "group1_id": options.get("group1Id"),
            "group2_id": options.get("group2Id"),
            "group1_clause_count": len(records_a),
            "group2_clause_count": len(records_b),
            "matched_pair_count": len(analyzed),
            "unmatched_group1_count": len(unmatched_a),
            "unmatched_group2_count": len(unmatched_b),
            "scoring_basis": total_basis,
            "thresholds": {
                "similarity_threshold": sim_threshold,
                "conflict_threshold": conflict_threshold,
                "high_match_threshold": high_match_threshold,
                "confidence_threshold": confidence_threshold,
            },
            "pipeline": pipeline_meta,
            "priority_order_by": "priority_score_desc",
            "selected_priority_rules": selected_rules,
        },
    }
