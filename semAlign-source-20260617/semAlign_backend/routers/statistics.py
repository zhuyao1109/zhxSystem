"""标准库统计 — GET /api/statistics（与 mvp 一致）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from models.standard import Standard
from models.user import User
from schemas.base import APIResponse

router = APIRouter(tags=["标准管理"])


@router.get("/statistics", response_model=APIResponse[Dict[str, Any]])
async def get_statistics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取标准库统计信息。"""
    total = db.query(Standard).count()
    dept_stats: Dict[str, int] = {}
    for std in db.query(Standard).all():
        dept = std.department or "其他"
        dept_stats[dept] = dept_stats.get(dept, 0) + 1
    return APIResponse(
        data={
            "total_standards": total,
            "department_stats": dept_stats,
            "last_update": datetime.now().isoformat(),
        }
    )
