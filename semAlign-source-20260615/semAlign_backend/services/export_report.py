"""Excel 比对报告导出 — 与 mvp 导出逻辑一致。"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

import pandas as pd

from services.comparison_payloads import get_conflicts_payload, get_solutions_payload


def build_report_excel_bytes(task_id: str) -> tuple[bytes, str]:
    """
    生成 Excel 文件字节与建议文件名。

    Returns:
        (file_bytes, filename)
    """
    task_info: Dict[str, Any] = {
        "任务ID": task_id,
        "标准组1": "中航信航班准点率标准 v2.3",
        "标准组2": "ICAO 航班运行统计标准 v4.1",
        "比对时间": "2023-10-15 14:30:25",
        "对齐模式": "自动对齐",
        "优先级规则": "国际标准优先, 最新修订优先",
        "状态": "比对完成",
    }

    stats_info = {
        "指标": ["冲突率", "匹配率", "待确认率"],
        "数值": ["32%", "58%", "10%"],
    }

    solutions: List[Dict[str, Any]] = []
    for s in get_solutions_payload():
        solutions.append(
            {
                "冲突点": s["title"],
                "严重程度": s["severity"],
                "推荐方案": s["description"],
                "推荐依据": s["reason"],
                "赞成数": s["approve_count"],
                "反对数": s["reject_count"],
            }
        )

    conflicts: List[Dict[str, Any]] = []
    for c in get_conflicts_payload():
        conflicts.append(
            {
                "冲突ID": c["id"],
                "冲突点": c["title"],
                "中航信标准": c["standard1"]["content"],
                "ICAO标准": c["standard2"]["content"],
            }
        )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([task_info]).to_excel(writer, sheet_name="任务信息", index=False)
        pd.DataFrame(stats_info).to_excel(writer, sheet_name="统计信息", index=False)
        pd.DataFrame(solutions).to_excel(writer, sheet_name="解决方案", index=False)
        pd.DataFrame(conflicts).to_excel(writer, sheet_name="冲突详情", index=False)
        summary_data = {
            "生成时间": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "报告类型": ["标准比对结果报告"],
            "总冲突数": [len(conflicts)],
            "高冲突数": [1],
            "中冲突数": [1],
            "低冲突数": [1],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="报告摘要", index=False)

    output.seek(0)
    filename = f'比对报告_{task_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return output.read(), filename
