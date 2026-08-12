"""冲突问答数据路由 - 提供问答冲突概览与列表（临时展示）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.deps import get_current_admin_user, get_db
from models import ConflictDialogue, ConflictDialogueMapping, TermConflict, Term
from models.user import User
from schemas.base import APIResponse

router = APIRouter(prefix="/conflict-dialogues", tags=["冲突问答"])


class ConflictDialogueRow(BaseModel):
    id: int
    dialogue_id: str
    original_conflict_id: str
    question: str
    conflict_type: str
    source_document: str
    cluster: str


class TermConflictContentRow(BaseModel):
    id: int
    term_name: str
    standard_no_1: str
    standard_no_2: str
    conflict_type: str
    conflict_desc: str
    source_file: str


class ConflictDialogueOverviewData(BaseModel):
    total_dialogues: int
    total_conflict_groups: int
    total_mappings: int
    mapped_conflict_groups: int
    total_term_conflicts: int
    rows: list[ConflictDialogueRow]
    term_conflict_rows: list[TermConflictContentRow]


@router.get("/overview", response_model=APIResponse[ConflictDialogueOverviewData])
async def get_conflict_dialogues_overview(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """获取冲突问答概览与最近记录。"""
    try:
        total_dialogues = db.query(func.count(ConflictDialogue.id)).scalar() or 0
        total_conflict_groups = (
            db.query(func.count(func.distinct(ConflictDialogue.original_conflict_id))).scalar() or 0
        )
        total_mappings = db.query(func.count(ConflictDialogueMapping.id)).scalar() or 0
        mapped_conflict_groups = (
            db.query(func.count(func.distinct(ConflictDialogueMapping.original_conflict_id))).scalar() or 0
        )
        total_term_conflicts = db.query(func.count(TermConflict.id)).scalar() or 0

        rows = (
            db.query(ConflictDialogue)
            .order_by(ConflictDialogue.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        term_conflict_rows = (
            db.query(TermConflict, Term.name.label("term_name"))
            .join(Term, Term.id == TermConflict.term_id)
            .order_by(TermConflict.id.desc())
            .limit(size)
            .all()
        )
    except OperationalError:
        return APIResponse(
            data=ConflictDialogueOverviewData(
                total_dialogues=0,
                total_conflict_groups=0,
                total_mappings=0,
                mapped_conflict_groups=0,
                total_term_conflicts=0,
                rows=[],
                term_conflict_rows=[],
            )
        )

    return APIResponse(
        data=ConflictDialogueOverviewData(
            total_dialogues=total_dialogues,
            total_conflict_groups=total_conflict_groups,
            total_mappings=total_mappings,
            mapped_conflict_groups=mapped_conflict_groups,
            total_term_conflicts=total_term_conflicts,
            rows=[
                ConflictDialogueRow(
                    id=item.id,
                    dialogue_id=item.dialogue_id,
                    original_conflict_id=item.original_conflict_id,
                    question=item.question,
                    conflict_type=item.conflict_type,
                    source_document=item.source_document,
                    cluster=item.cluster,
                )
                for item in rows
            ],
            term_conflict_rows=[
                TermConflictContentRow(
                    id=item.TermConflict.id,
                    term_name=item.term_name,
                    standard_no_1=item.TermConflict.standard_no_1,
                    standard_no_2=item.TermConflict.standard_no_2,
                    conflict_type=item.TermConflict.conflict_type,
                    conflict_desc=item.TermConflict.conflict_desc,
                    source_file=item.TermConflict.source_file,
                )
                for item in term_conflict_rows
            ],
        )
    )
