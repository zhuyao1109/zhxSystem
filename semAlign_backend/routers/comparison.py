"""比对结果路由 — 与 mvp `/api/comparison/*` 契约一致。

从 alignment_tasks.result_json 读取真实对齐结果，提供统计、聚类、冲突分页、
报告文本及用户反馈落库能力。所有接口均校验任务归属与发布权限。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from models.alignment_task import AlignmentTask
from models.comparison_feedback import ComparisonFeedback, ComparisonModification
from models.user import User
from schemas.base import APIResponse

router = APIRouter(prefix="/comparison", tags=["比对结果"])


def _parse_task_id(task_id: str | int) -> int:
    """函数内部辅助：parse task id。"""
    try:
        numeric_id = int(task_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="task_id 格式错误") from exc
    if numeric_id <= 0:
        raise HTTPException(status_code=400, detail="task_id 格式错误")
    return numeric_id


def _get_owned_task(task_id: str | int, db: Session, current_user: User) -> AlignmentTask:
    """函数内部辅助：get owned task。"""
    numeric_id = _parse_task_id(task_id)

    task = db.query(AlignmentTask).filter(AlignmentTask.id == numeric_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if current_user.role != "admin" and task.user_id != current_user.id and task.review_status != "published":
        raise HTTPException(status_code=403, detail="无权查看该对齐结果")
    return task


def _get_task_result(task_id: str, db: Session, current_user: User) -> dict[str, Any]:
    """函数内部辅助：get task result。"""
    task = _get_owned_task(task_id, db, current_user)
    if task.status != "completed" or not isinstance(task.result_json, dict):
        raise HTTPException(status_code=409, detail="任务尚未完成或无有效对齐结果")
    return task.result_json


@router.get("/task/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_comparison_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取比对任务信息（读取真实对齐结果）。"""
    task = _get_owned_task(task_id, db, current_user)
    payload = _get_task_result(task_id, db, current_user)
    return APIResponse(
        data={
            "id": task_id,
            "standard_group1": payload.get("standard_group1"),
            "standard_group2": payload.get("standard_group2"),
            "comparison_time": payload.get("comparison_time"),
            "alignment_mode": payload.get("alignment_mode", "自动对齐"),
            "priority_rules": payload.get("priority_rules", "默认规则"),
            "status": payload.get("status", "比对完成"),
            "review_status": task.review_status,
            "review_notes": task.review_notes,
            "published_at": task.published_at.isoformat() if task.published_at else None,
        }
    )


@router.get("/stats/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_comparison_stats(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取比对统计。"""
    payload = _get_task_result(task_id, db, current_user)
    return APIResponse(data=payload.get("stats") or {"conflict_rate": 0, "match_rate": 0, "pending_rate": 0})


@router.get("/clusters/{task_id}", response_model=APIResponse[List[Dict[str, Any]]])
async def get_semantic_clusters(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[Dict[str, Any]]]:
    """获取语义聚类数据。"""
    payload = _get_task_result(task_id, db, current_user)
    return APIResponse(data=payload.get("clusters") or [])


@router.get("/conflicts/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_conflicts(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取冲突点列表，支持服务端分页。"""
    payload = _get_task_result(task_id, db, current_user)
    conflicts = payload.get("conflicts") or []
    total = len(conflicts)
    start = (page - 1) * size
    end = start + size
    return APIResponse(
        data={
            "data": conflicts[start:end],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if size else 0,
        }
    )


@router.get("/solutions/{task_id}", response_model=APIResponse[List[Dict[str, Any]]])
async def get_solutions(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[Dict[str, Any]]]:
    """获取解决方案列表。"""
    payload = _get_task_result(task_id, db, current_user)
    return APIResponse(data=payload.get("solutions") or [])


@router.get("/report/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_conflict_report(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取第四层生成的自然语言冲突检测报告。"""
    payload = _get_task_result(task_id, db, current_user)
    pipeline = (payload.get("meta") or {}).get("pipeline") or {}
    return APIResponse(
        data={
            "task_id": task_id,
            "report_text": payload.get("report_text") or "",
            "pipeline_version": pipeline.get("version"),
            "layers": pipeline.get("layers"),
        }
    )


@router.post("/feedback", response_model=APIResponse[Dict[str, Any]])
async def submit_feedback(
    feedback: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """提交用户赞成/反对反馈（真实落库）。"""
    task_id_raw = feedback.get("task_id")
    if task_id_raw is None:
        raise HTTPException(status_code=400, detail="缺少必要字段: task_id")
    task = _get_owned_task(task_id_raw, db, current_user)

    conflict_id = str(feedback.get("conflict_id") or "").strip()
    if not conflict_id:
        raise HTTPException(status_code=400, detail="缺少必要字段: conflict_id")

    raw_type = str(
        feedback.get("feedback_type")
        or feedback.get("action")
        or feedback.get("type")
        or ""
    ).strip().lower()
    type_map = {
        "approve": "approve",
        "赞成": "approve",
        "support": "approve",
        "yes": "approve",
        "reject": "reject",
        "反对": "reject",
        "disagree": "reject",
        "no": "reject",
    }
    feedback_type = type_map.get(raw_type)
    if feedback_type is None:
        raise HTTPException(status_code=400, detail="feedback_type 仅支持 approve/reject")

    record = ComparisonFeedback(
        task_id=task.id,
        conflict_id=conflict_id,
        feedback_type=feedback_type,
        comment=str(feedback.get("comment") or "").strip() or None,
        user_id=current_user.id,
        user_name=current_user.username,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return APIResponse(
        data={
            "status": "success",
            "message": "反馈已记录",
            "feedback_id": str(record.id),
            "task_id": str(task.id),
            "conflict_id": conflict_id,
            "feedback_type": feedback_type,
            "timestamp": record.created_at.isoformat() if record.created_at else datetime.now().isoformat(),
        }
    )


@router.get("/feedback/{conflict_id}", response_model=APIResponse[Dict[str, Any]])
async def get_feedback_counts_route(
    conflict_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取某个冲突的反馈统计。"""
    approve = (
        db.query(func.count(ComparisonFeedback.id))
        .filter(
            ComparisonFeedback.conflict_id == conflict_id,
            ComparisonFeedback.feedback_type == "approve",
        )
        .scalar()
        or 0
    )
    reject = (
        db.query(func.count(ComparisonFeedback.id))
        .filter(
            ComparisonFeedback.conflict_id == conflict_id,
            ComparisonFeedback.feedback_type == "reject",
        )
        .scalar()
        or 0
    )
    return APIResponse(data={"approve": int(approve), "reject": int(reject)})


@router.post("/feedback/modification", response_model=APIResponse[Dict[str, Any]])
async def submit_modification(
    feedback: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """提交修改意见。"""
    required_fields = ["task_id", "type", "content"]
    for field in required_fields:
        if field not in feedback or str(feedback.get(field) or "").strip() == "":
            raise HTTPException(status_code=400, detail=f"缺少必要字段: {field}")

    task = _get_owned_task(str(feedback["task_id"]), db, current_user)
    mod_type = str(feedback["type"]).strip()
    content = str(feedback["content"]).strip()

    record = ComparisonModification(
        task_id=task.id,
        modification_type=mod_type,
        content=content,
        user_id=current_user.id,
        user_name=current_user.username,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return APIResponse(
        data={
            "status": "success",
            "message": "修改意见已提交",
            "feedback_id": str(record.id),
            "timestamp": record.created_at.isoformat() if record.created_at else datetime.now().isoformat(),
        }
    )


@router.get("/feedback/modification/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_modifications(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取某个任务的所有修改意见（真实数据）。"""
    task = _get_owned_task(task_id, db, current_user)
    rows = (
        db.query(ComparisonModification)
        .filter(ComparisonModification.task_id == task.id)
        .order_by(ComparisonModification.created_at.desc())
        .all()
    )
    return APIResponse(
        data={
            "task_id": str(task.id),
            "modifications": [
                {
                    "id": str(row.id),
                    "type": row.modification_type,
                    "content": row.content,
                    "user_name": row.user_name,
                    "timestamp": row.created_at.isoformat() if row.created_at else "",
                }
                for row in rows
            ],
        }
    )
