"""比对结果演示数据 — 与 mvp/src/api/endpoints.py 中比对接口保持一致，便于前端联调。

注意：
    生产环境比对数据以 routers/comparison.py 读取的任务结果为准；
    本模块仅用于无后端任务时的静态演示与单元测试夹具。
"""

from __future__ import annotations

from typing import Any, Dict, List

SOURCE_CATA = "中航信标准"
SOURCE_ICAO = "ICAO 标准"
SOLUTION_CREATE_TIME = "2023-10-18 09:45:32"


def get_comparison_task_payload(task_id: str) -> Dict[str, Any]:
    """返回比对任务概览演示数据（MVP 联调用）。"""
    return {
        "id": task_id,
        "standard_group1": "中航信航班准点率标准 v2.3",
        "standard_group2": "ICAO 航班运行统计标准 v4.1",
        "comparison_time": "2023-10-15 14:30:25",
        "alignment_mode": "自动对齐",
        "priority_rules": "国际标准优先, 最新修订优先",
        "status": "比对完成",
    }


def get_comparison_stats_payload() -> Dict[str, Any]:
    """返回冲突率/匹配率等统计演示数据。"""
    return {
        "conflict_rate": 32,
        "match_rate": 58,
        "pending_rate": 10,
    }


def get_semantic_clusters_payload() -> List[Dict[str, Any]]:
    """返回语义聚类列表演示数据。"""
    return [
        {
            "title": "准点率定义与计算",
            "clause_count": 8,
            "cluster_type": 1,
            "clauses": [
                {
                    "source": SOURCE_CATA,
                    "content": "准点率 = 实际起飞时间 / 计划起飞时间",
                    "is_conflict": False,
                },
                {
                    "source": SOURCE_ICAO,
                    "content": "延误 15 分钟以上计为非准点",
                    "is_conflict": True,
                    "conflict_marker": "15 分钟以上",
                },
                {
                    "source": SOURCE_CATA,
                    "content": "准点率统计应排除天气原因导致的延误",
                    "is_conflict": False,
                },
            ],
        },
        {
            "title": "航班状态分类",
            "clause_count": 6,
            "cluster_type": 2,
            "clauses": [
                {
                    "source": SOURCE_CATA,
                    "content": "航班状态分为：计划、值机、登机、起飞、到达、取消",
                    "is_conflict": False,
                },
                {
                    "source": SOURCE_ICAO,
                    "content": "航班状态分为：计划、运行中、完成、取消、备降",
                    "is_conflict": False,
                },
            ],
        },
        {
            "title": "数据上报要求",
            "clause_count": 5,
            "cluster_type": 3,
            "clauses": [
                {
                    "source": SOURCE_CATA,
                    "content": "航空公司需在航班起飞后 2 小时内上报准点数据",
                    "is_conflict": True,
                    "conflict_marker": "2 小时内",
                },
                {
                    "source": SOURCE_ICAO,
                    "content": "航空公司需在航班起飞后 24 小时内上报运行数据",
                    "is_conflict": True,
                    "conflict_marker": "24 小时内",
                },
            ],
        },
        {
            "title": "延误原因分类",
            "clause_count": 7,
            "cluster_type": 4,
            "clauses": [
                {
                    "source": SOURCE_CATA,
                    "content": "延误原因分为：航空公司原因、空管原因、天气原因、机场原因",
                    "is_conflict": False,
                },
                {
                    "source": SOURCE_ICAO,
                    "content": "延误原因分为：航司可控原因、航司不可控原因",
                    "is_conflict": False,
                },
            ],
        },
    ]


def get_conflicts_payload() -> List[Dict[str, Any]]:
    """返回冲突点列表演示数据。"""
    return [
        {
            "id": "conflict-1",
            "title": "准点率定义冲突",
            "severity": "高冲突",
            "standard1": {
                "name": SOURCE_CATA,
                "content": "准点率 = 实际起飞时间 / 计划起飞时间，计算结果以百分比表示。",
            },
            "standard2": {
                "name": SOURCE_ICAO,
                "content": "延误 15 分钟以上计为非准点，准点率为准点航班数量与总航班数量之比。",
            },
        },
        {
            "id": "conflict-2",
            "title": "数据上报时限冲突",
            "severity": "中冲突",
            "standard1": {
                "name": SOURCE_CATA,
                "content": "航空公司需在航班起飞后 2 小时内上报准点数据。",
            },
            "standard2": {
                "name": SOURCE_ICAO,
                "content": "航空公司需在航班起飞后 24 小时内上报运行数据。",
            },
        },
        {
            "id": "conflict-3",
            "title": "延误原因分类冲突",
            "severity": "低冲突",
            "standard1": {
                "name": SOURCE_CATA,
                "content": "延误原因分为：航空公司原因、空管原因、天气原因、机场原因、其他原因。",
            },
            "standard2": {
                "name": SOURCE_ICAO,
                "content": "延误原因分为：航司可控原因、航司不可控原因。",
            },
        },
    ]


def get_solutions_payload() -> List[Dict[str, Any]]:
    """返回解决方案列表演示数据。"""
    return [
        {
            "conflict_id": "conflict-1",
            "title": "准点率定义冲突",
            "severity": "高冲突",
            "description": (
                "采用ICAO标准定义，将\"延误15分钟以上计为非准点\"作为准点率计算基准，"
                "同时保留中航信标准中排除天气原因导致延误的条款。"
            ),
            "reason": "国际标准优先原则；ICAO标准在全球航空业应用更广泛，有利于国际数据对比。",
            "creator": "李工程师",
            "create_time": SOLUTION_CREATE_TIME,
            "approve_count": 12,
            "reject_count": 3,
        },
        {
            "conflict_id": "conflict-2",
            "title": "数据上报时限冲突",
            "severity": "中冲突",
            "description": (
                "采用分级上报机制：关键准点数据2小时内上报，完整运行数据24小时内上报。"
            ),
            "reason": "平衡实时性需求与国际标准兼容性；满足国内运营实时监控需求，同时符合国际数据上报规范。",
            "creator": "李工程师",
            "create_time": SOLUTION_CREATE_TIME,
            "approve_count": 8,
            "reject_count": 2,
        },
        {
            "conflict_id": "conflict-3",
            "title": "延误原因分类冲突",
            "severity": "低冲突",
            "description": (
                "保留中航信详细分类，同时映射到ICAO两大分类：航空公司原因对应航司可控原因，"
                "其他原因对应航司不可控原因。"
            ),
            "reason": "保留操作层面的详细分类有利于问题定位，同时通过映射机制满足国际标准上报要求。",
            "creator": "李工程师",
            "create_time": SOLUTION_CREATE_TIME,
            "approve_count": 15,
            "reject_count": 1,
        },
    ]


def get_feedback_counts(conflict_id: str) -> Dict[str, int]:
    """返回赞成/反对计数演示数据。"""
    counts: Dict[str, Dict[str, int]] = {
        "conflict-1": {"approve": 12, "reject": 3},
        "conflict-2": {"approve": 8, "reject": 2},
        "conflict-3": {"approve": 15, "reject": 1},
    }
    return counts.get(conflict_id, {"approve": 0, "reject": 0})


def get_modifications_payload(task_id: str) -> Dict[str, Any]:
    """返回修改意见列表演示数据。"""
    return {
        "task_id": task_id,
        "modifications": [
            {
                "id": "mod-1",
                "type": "suggestion",
                "content": "建议增加更多关于天气因素的考虑",
                "user_name": "王研究员",
                "timestamp": "2023-10-19T10:30:00",
            }
        ],
    }
