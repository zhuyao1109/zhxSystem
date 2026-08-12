"""规则引擎编排 — 封装 RuleOrchestrator 的默认配置与评估。"""

from __future__ import annotations

from typing import Any, Dict

from services.rule_engine.rule_orchestrator import RuleOrchestrator


def default_rule_config() -> Dict[str, Any]:
    return {
        "enabled_rules": {
            "international_priority": True,
            "latest_revision": True,
            "mandatory_priority": True,
        },
        "strategy": "weighted_sum",
        "weights": {
            "international_priority": 0.4,
            "latest_revision": 0.3,
            "mandatory_priority": 0.3,
        },
    }


def list_rules_payload() -> Dict[str, Any]:
    return {
        "rules": [
            {
                "id": "international_priority",
                "name": "国际标准优先",
                "description": "优先采用国际标准（IATA、ICAO、ISO等）",
                "default_enabled": True,
            },
            {
                "id": "latest_revision",
                "name": "最新修订优先",
                "description": "优先采用修订日期较新的标准",
                "default_enabled": True,
            },
            {
                "id": "mandatory_priority",
                "name": "强制性标准优先",
                "description": "优先采用强制性要求（必须、应、shall等）",
                "default_enabled": True,
            },
        ]
    }


def evaluate_conflict_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 RuleOrchestrator 评估请求中的冲突结构。
    请求格式与 mvp `/rules/evaluate` 一致。
    """
    conflict_data = {
        "clause_a": request.get("conflict", {}).get("clause_a", {}),
        "clause_b": request.get("conflict", {}).get("clause_b", {}),
    }
    config = request.get("config") or default_rule_config()
    orchestrator = RuleOrchestrator(config)
    result = orchestrator.evaluate(conflict_data)
    return {
        "conflict_id": request.get("conflict", {}).get("id", ""),
        **result,
    }
