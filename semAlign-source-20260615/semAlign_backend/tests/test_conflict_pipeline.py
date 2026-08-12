"""冲突识别流水线测试。"""

from __future__ import annotations

from types import SimpleNamespace

from services.alignment_executor import _Clause, _build_standard_meta, _priority_config_from_selected
from services.conflict_pipeline.pipeline import run_four_layer_pipeline
from services.conflict_pipeline.layer1_recall import recall_candidate_pairs
from services.conflict_pipeline.models import ClauseRecord


TEXT_A = (
    "1.1 组织应建立信息安全管理制度并明确管理职责。"
    "1.2 组织应定期开展信息安全风险评估并保留评估记录。"
)

TEXT_B = (
    "2.1 组织必须建立信息安全控制措施。"
    "2.2 组织应每年开展一次安全审计并提交报告。"
)


def _records(text: str) -> list[ClauseRecord]:
    return [
        ClauseRecord(idx=c.idx, text=c.text, section=c.section, page=c.page)
        for c in [
            _Clause(idx=0, text="1.1 组织应建立信息安全管理制度并明确管理职责。", section="1.1", page=1),
            _Clause(idx=1, text="1.2 组织应定期开展信息安全风险评估并保留评估记录。", section="1.2", page=1),
        ]
    ]


def _align_fn(a: list[ClauseRecord], b: list[ClauseRecord], threshold: float):
    pairs = []
    for ca in a:
        for cb in b:
            pairs.append(
                {
                    "a_idx": ca.idx,
                    "b_idx": cb.idx,
                    "score": 0.5,
                    "a_text": ca.text,
                    "b_text": cb.text,
                    "a_section": ca.section,
                    "b_section": cb.section,
                    "match_type": "test",
                }
            )
    return pairs


class TestConflictPipeline:
    def test_layer1_recall(self):
        ra = _records(TEXT_A)
        rb = _records(TEXT_B)
        pairs, meta = recall_candidate_pairs(ra, rb, _align_fn, 0.3)
        assert pairs
        assert "candidate_pair_count" in meta

    def test_run_four_layer_pipeline(self):
        std_a = SimpleNamespace(standard_no="GB/T 1", name="标准A", status="有效")
        std_b = SimpleNamespace(standard_no="ISO 2", name="标准B", status="有效")
        clauses_a = [
            _Clause(idx=0, text="1.1 组织应建立信息安全管理制度并明确管理职责。", section="1.1", page=1),
            _Clause(idx=1, text="1.2 组织应定期开展信息安全风险评估并保留评估记录。", section="1.2", page=1),
        ]
        clauses_b = [
            _Clause(idx=0, text="2.1 组织必须建立信息安全控制措施并落实责任人。", section="2.1", page=1),
            _Clause(idx=1, text="2.2 组织应每年开展一次安全审计并提交报告。", section="2.2", page=1),
        ]
        result = run_four_layer_pipeline(
            standard_a=std_a,
            standard_b=std_b,
            clauses_a=clauses_a,
            clauses_b=clauses_b,
            align_fn=_align_fn,
            build_meta_fn=_build_standard_meta,
            priority_config_fn=_priority_config_from_selected,
            options={"enableLayer3": True, "similarityThreshold": 0.2},
            standards_catalog=[],
        )
        assert "conflicts" in result
        assert "solutions" in result
        assert result["meta"]["pipeline"]["version"] == "4-layer-v1"


class TestLayer4Adjudication:
    def test_severity_and_priority_helpers(self):
        from services.conflict_pipeline.layer4_adjudication import (
            _priority_score,
            _severity,
            build_solutions,
            conflicts_to_legacy_dict,
        )
        from services.conflict_pipeline.models import AdjudicatedConflict, Layer3Result

        assert _severity(0.5, 0.6) == "中冲突"
        assert _severity(0.7, 0.3) == "低冲突"
        l3 = Layer3Result(
            triggered=True,
            abolition_hits=[{"id": "a1"}],
            replacement_hits=[],
        )
        score = _priority_score(0.5, 0.6, 0.5, 2, l3, ["comprehensive"])
        assert score > 0

        conflict = AdjudicatedConflict(
            id="conflict-1",
            title="测试冲突",
            severity="高冲突",
            similarity_score=0.4,
            conflict_confidence=0.8,
            authority_score=0.7,
            standard1={"name": "标准A"},
            standard2={"name": "标准B"},
            location={},
            priority_score=score,
            priority_rank=1,
            priority_recommendation="采用A",
            priority_confidence=0.7,
            priority_rule_details={},
            atomic_differences=[{"description": "术语差异"}],
            layer3={"triggered": True},
            adjudication_summary="摘要",
        )
        legacy = conflicts_to_legacy_dict([conflict])
        assert legacy[0]["id"] == "conflict-1"
        solutions = build_solutions([conflict])
        assert solutions[0]["conflict_id"] == "conflict-1"
