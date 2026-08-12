"""四层冲突识别流水线 — 数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClauseRecord:
    idx: int
    text: str
    section: str = "正文"
    page: int | None = None
    start_char: int | None = None
    citations: list[str] = field(default_factory=list)


@dataclass
class CandidatePair:
    """第一层粗召回候选对。"""

    a_idx: int
    b_idx: int
    recall_score: float
    a_text: str
    b_text: str
    a_section: str = "正文"
    b_section: str = "正文"
    a_page: int | None = None
    b_page: int | None = None
    a_start_char: int | None = None
    b_start_char: int | None = None
    recall_sources: list[str] = field(default_factory=list)
    match_type: str = "semantic"


@dataclass
class Layer2Result:
    """第二层多智能体输出。"""

    authority_score: float
    authority_recommendation: str
    authority_rule_details: dict[str, Any]
    atomic_differences: list[dict[str, Any]]
    conflict_confidence: float
    uncertainty_factors: list[str]
    is_low_confidence: bool
    similarity_score: float
    match_type: str


@dataclass
class Layer3Result:
    """第三层主动信息探寻。"""

    triggered: bool
    abolition_hits: list[dict[str, Any]] = field(default_factory=list)
    replacement_hits: list[dict[str, Any]] = field(default_factory=list)
    citation_chain: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


@dataclass
class AdjudicatedConflict:
    """第四层裁决后的冲突项。"""

    id: str
    title: str
    severity: str
    similarity_score: float
    conflict_confidence: float
    authority_score: float
    standard1: dict[str, Any]
    standard2: dict[str, Any]
    location: dict[str, Any]
    priority_score: float
    priority_rank: int
    priority_recommendation: str
    priority_confidence: float
    priority_rule_details: dict[str, Any]
    atomic_differences: list[dict[str, Any]]
    layer3: dict[str, Any]
    adjudication_summary: str
