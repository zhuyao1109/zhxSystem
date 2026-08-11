"""导出报告路由 — GET /api/export/report/{task_id}"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core.deps import get_current_user
from models.user import User
from services.export_report import build_report_excel_bytes

router = APIRouter(prefix="/export", tags=["导出报告"])


@router.get("/report/{task_id}")
async def export_report(
    task_id: str,
    _current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """导出比对报告为 Excel 文件。"""
    content, filename = build_report_excel_bytes(task_id)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
