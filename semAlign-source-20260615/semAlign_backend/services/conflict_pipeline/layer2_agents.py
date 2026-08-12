"""第二层：多智能体精细检测 — 层级仲裁 / 原子比较 / 不确定性量化。"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from services.rule_engine.rule_orchestrator import RuleOrchestrator

from .models import CandidatePair, Layer2Result

_MANDATORY_KW = ("必须", "应", "shall", "must", "required", "不得", "禁止")
_NUM_PATTERN = re.compile(r"\d+(?:\.\d+)?%?")


class HierarchicalArbitrationAgent:
    """层级仲裁智能体 — 输出权威性分数与规则建议。"""

    def __init__(self, orchestrator: RuleOrchestrator):
        self.orchestrator = orchestrator

    def run(
        self,
        pair: CandidatePair,
        meta_a: dict[str, Any],
        meta_b: dict[str, Any],
    ) -> tuple[float, str, dict[str, Any]]:
        eval_result = self.orchestrator.evaluate(
            {
                "clause_a": {"text": pair.a_text, "document_metadata": meta_a},
                "clause_b": {"text": pair.b_text, "document_metadata": meta_b},
            }
        )
        confidence = float(eval_result.get("confidence", 0.0) or 0.0)
        requires_user = bool(eval_result.get("requires_user_decision", True))
        authority_score = round(confidence * (0.65 if requires_user else 1.0), 4)
        recommendation = str(eval_result.get("final_recommendation") or "需要人工决策")
        return authority_score, recommendation, dict(eval_result.get("rule_details") or {})


class AtomizedComparisonAgent:
    """原子化比较智能体 — 术语/数值/强制性表述差异。"""

    def run(self, pair: CandidatePair) -> list[dict[str, Any]]:
        diffs: list[dict[str, Any]] = []
        ta, tb = pair.a_text, pair.b_text

        ma = {k for k in _MANDATORY_KW if k in ta}
        mb = {k for k in _MANDATORY_KW if k in tb}
        if ma != mb:
            diffs.append(
                {
                    "dimension": "mandatory_wording",
                    "left": sorted(ma) or ["无"],
                    "right": sorted(mb) or ["无"],
                    "description": "强制性表述不一致",
                }
            )

        na = set(_NUM_PATTERN.findall(ta))
        nb = set(_NUM_PATTERN.findall(tb))
        only_a = na - nb
        only_b = nb - na
        if only_a or only_b:
            diffs.append(
                {
                    "dimension": "numeric_threshold",
                    "left": sorted(only_a)[:8],
                    "right": sorted(only_b)[:8],
                    "description": "数值或阈值表述存在差异",
                }
            )

        tokens_a = set(re.findall(r"[\u4e00-\u9fff]{2,}", ta))
        tokens_b = set(re.findall(r"[\u4e00-\u9fff]{2,}", tb))
        term_diff_a = sorted(tokens_a - tokens_b)[:6]
        term_diff_b = sorted(tokens_b - tokens_a)[:6]
        if term_diff_a or term_diff_b:
            diffs.append(
                {
                    "dimension": "terminology",
                    "left": term_diff_a,
                    "right": term_diff_b,
                    "description": "关键术语集合不一致",
                }
            )

        seq_ratio = SequenceMatcher(None, ta[:300], tb[:300]).ratio()
        if seq_ratio < 0.55 and not diffs:
            diffs.append(
                {
                    "dimension": "semantic_divergence",
                    "left": ta[:80],
                    "right": tb[:80],
                    "description": "条款整体语义偏离较大",
                }
            )
        return diffs


class UncertaintyQuantificationAgent:
    """不确定性量化智能体 — 冲突置信度与是否触发第三层。"""

    def __init__(self, confidence_threshold: float = 0.55):
        self.confidence_threshold = confidence_threshold

    def run(
        self,
        pair: CandidatePair,
        similarity_score: float,
        authority_score: float,
        atomic_diff_count: int,
        conflict_threshold: float,
    ) -> tuple[float, list[str], bool]:
        factors: list[str] = []
        # 相似度越接近冲突阈值，不确定性越高
        margin = abs(similarity_score - conflict_threshold)
        margin_uncertainty = max(0.0, 1.0 - margin * 4.0)
        if margin_uncertainty > 0.35:
            factors.append("similarity_near_conflict_threshold")

        if len(pair.a_text) < 40 or len(pair.b_text) < 40:
            factors.append("short_clause_text")

        if atomic_diff_count == 0 and similarity_score < conflict_threshold:
            factors.append("low_similarity_without_atomic_diff")

        if authority_score < 0.45:
            factors.append("weak_authority_signal")

        if "citation_expansion" in " ".join(pair.recall_sources):
            factors.append("citation_only_recall")

        # 置信度：有原子差异 + 明确低相似 → 高；边界情况 → 低
        base = 0.35
        if similarity_score < conflict_threshold - 0.12:
            base += 0.35
        if atomic_diff_count > 0:
            base += min(0.25, 0.08 * atomic_diff_count)
        base += authority_score * 0.2
        base -= margin_uncertainty * 0.25
        base -= 0.1 * len(factors)

        confidence = round(max(0.05, min(0.98, base)), 4)
        is_low = confidence < self.confidence_threshold
        return confidence, factors, is_low


def run_layer2(
    candidates: list[CandidatePair],
    meta_a: dict[str, Any],
    meta_b: dict[str, Any],
    orchestrator: RuleOrchestrator,
    *,
    conflict_threshold: float,
    confidence_threshold: float,
) -> tuple[list[tuple[CandidatePair, Layer2Result]], dict[str, Any]]:
    arbiter = HierarchicalArbitrationAgent(orchestrator)
    atomizer = AtomizedComparisonAgent()
    uncertainty = UncertaintyQuantificationAgent(confidence_threshold)

    results: list[tuple[CandidatePair, Layer2Result]] = []
    low_confidence_count = 0

    for pair in candidates:
        sim = pair.recall_score
        auth_score, auth_rec, rule_details = arbiter.run(pair, meta_a, meta_b)
        atomic = atomizer.run(pair)
        conf, factors, is_low = uncertainty.run(
            pair, sim, auth_score, len(atomic), conflict_threshold
        )
        if is_low:
            low_confidence_count += 1

        results.append(
            (
                pair,
                Layer2Result(
                    authority_score=auth_score,
                    authority_recommendation=auth_rec,
                    authority_rule_details=rule_details,
                    atomic_differences=atomic,
                    conflict_confidence=conf,
                    uncertainty_factors=factors,
                    is_low_confidence=is_low,
                    similarity_score=sim,
                    match_type=pair.match_type,
                ),
            )
        )

    layer_meta = {
        "layer": 2,
        "analyzed_pairs": len(results),
        "low_confidence_count": low_confidence_count,
        "confidence_threshold": confidence_threshold,
    }
    return results, layer_meta
