"""术语冲突数据路由 - 提供术语冲突概览与列表（临时展示）"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_admin_user
from models.term_conflict import ImportBatch, Term, TermConflict
from models.user import User
from schemas.base import APIResponse

router = APIRouter(prefix="/term-conflicts", tags=["术语冲突"])


class TermConflictRow(BaseModel):
    """术语冲突行（前端展示）"""

    id: int
    term_name: str
    standard_no_1: str
    standard_no_2: str
    conflict_type: str
    conflict_desc: str
    source_file: str


class TermConflictOverviewData(BaseModel):
    """术语冲突概览数据"""

    total_conflicts: int
    total_terms: int
    total_types: int
    latest_batch_status: Optional[str] = None
    latest_batch_rows: int = 0
    rows: list[TermConflictRow]


@router.get("/overview", response_model=APIResponse[TermConflictOverviewData])
async def get_term_conflicts_overview(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="按术语名/标准号关键字筛选"),
    conflict_type: Optional[str] = Query(None, description="按冲突类型筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取术语冲突概览与列表。
    临时接口：用于标准库页面展示术语冲突数据情况。
    """
    base_query = db.query(TermConflict, Term.name.label("term_name")).join(
        Term, Term.id == TermConflict.term_id
    )

    if keyword:
        base_query = base_query.filter(
            or_(
                Term.name.contains(keyword),
                TermConflict.standard_no_1.contains(keyword),
                TermConflict.standard_no_2.contains(keyword),
            )
        )

    if conflict_type:
        base_query = base_query.filter(TermConflict.conflict_type == conflict_type)

    rows = (
        base_query.order_by(TermConflict.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    total_conflicts = db.query(func.count(TermConflict.id)).scalar() or 0
    total_terms = db.query(func.count(Term.id)).scalar() or 0
    total_types = db.query(func.count(func.distinct(TermConflict.conflict_type))).scalar() or 0

    latest_batch = db.query(ImportBatch).order_by(ImportBatch.id.desc()).first()

    result_rows = [
        TermConflictRow(
            id=item.TermConflict.id,
            term_name=item.term_name,
            standard_no_1=item.TermConflict.standard_no_1,
            standard_no_2=item.TermConflict.standard_no_2,
            conflict_type=item.TermConflict.conflict_type,
            conflict_desc=item.TermConflict.conflict_desc,
            source_file=item.TermConflict.source_file,
        )
        for item in rows
    ]

    return APIResponse(
        data=TermConflictOverviewData(
            total_conflicts=total_conflicts,
            total_terms=total_terms,
            total_types=total_types,
            latest_batch_status=latest_batch.status if latest_batch else None,
            latest_batch_rows=latest_batch.success_rows if latest_batch else 0,
            rows=result_rows,
        )
    )
