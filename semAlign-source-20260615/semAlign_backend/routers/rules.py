"""规则引擎路由 — 与 mvp `/api/rules/*` 一致。"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db
from models.user import User
from schemas.base import APIResponse
from services.rule_service import (
    default_rule_config,
    evaluate_conflict_request,
    list_rules_payload,
)

router = APIRouter(prefix="/rules", tags=["规则引擎"])


@router.post("/evaluate", response_model=APIResponse[Dict[str, Any]])
async def evaluate_conflict(
    request: Dict[str, Any],
    _db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """使用规则引擎评估冲突。"""
    try:
        data = evaluate_conflict_request(request)
        return APIResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list", response_model=APIResponse[Dict[str, Any]])
async def list_available_rules(
    _db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """列出所有可用规则。"""
    return APIResponse(data=list_rules_payload())


@router.get("/config/default", response_model=APIResponse[Dict[str, Any]])
async def get_default_rule_config_route(
    _db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取默认规则配置。"""
    return APIResponse(data=default_rule_config())
