"""标准管理路由 - 处理标准的 CRUD 操作"""

import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
import logging

from core.config import settings
from core.deps import get_db, get_current_admin_user, get_current_user
from models.user import User
from models.standard import Standard
from schemas.standard import (
    StandardCreate,
    StandardUpdate,
    StandardResponse,
    StandardListResponse
)
from schemas.base import APIResponse
from utils.document_processor import DocumentProcessor, get_chunk_store

router = APIRouter(prefix="/standards", tags=["标准管理"])
logger = logging.getLogger(__name__)

MSG_STANDARD_NOT_FOUND = "标准不存在"


def _build_file_id(standard: Standard) -> str:
    if standard.id is not None:
        return f"standard:{standard.id}"
    if standard.source_file:
        return f"source:{standard.source_file}"
    return f"source:{standard.standard_no}"


def _compose_index_text(standard: Standard) -> str:
    processor = DocumentProcessor()
    extracted = processor.load_saved_text(standard.source_file) if standard.source_file else None
    if extracted and extracted.strip():
        return extracted
    return "\n".join(
        part for part in [
            standard.standard_no,
            standard.name,
            standard.version,
            standard.status,
            standard.category,
            standard.department or "",
            standard.description or "",
        ] if part
    )


def _sync_vector_index(standard: Standard) -> None:
    chunk_store = get_chunk_store()
    if chunk_store is None:
        return
    chunk_store.upsert_text(
        _compose_index_text(standard),
        meta={
            "file_id": _build_file_id(standard),
            "standard_id": standard.id,
            "standard_no": standard.standard_no,
            "name": standard.name,
            "source": standard.source_file or f"{standard.standard_no}.txt",
            "source_file": standard.source_file,
        },
    )


def _resolve_data_dir(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    project_root = Path(__file__).resolve().parents[1]
    return (project_root / path).resolve()


def _sanitize_filename_fragment(value: str) -> str:
    illegal = '\\/:*?"<>|'
    return "".join("_" if ch in illegal else ch for ch in value).strip()


def _find_original_upload_path(standard: Standard) -> Optional[Path]:
    source_file = (standard.source_file or "").strip()
    if not source_file:
        return None

    upload_dir = _resolve_data_dir(settings.upload_dir)
    if not upload_dir.exists():
        return None

    source_name = Path(source_file).name
    candidates: List[Path] = []
    direct = upload_dir / source_name
    if direct.is_file():
        candidates.append(direct)

    candidates.extend([p for p in upload_dir.glob(f"*_{source_name}") if p.is_file()])
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_saved_text_path(standard: Standard) -> Optional[Path]:
    text_dir = _resolve_data_dir(settings.text_output_dir)
    if not text_dir.exists():
        return None

    source_file = (standard.source_file or "").strip()
    source_name = Path(source_file).name if source_file else ""
    source_stem = Path(source_name).stem if source_name else ""
    standard_no_stem = _sanitize_filename_fragment((standard.standard_no or "").strip())

    patterns: List[str] = []
    if source_stem:
        patterns.extend([f"{source_stem}.txt", f"*_{source_stem}.txt"])
    if standard_no_stem:
        patterns.extend([f"{standard_no_stem}.txt", f"*_{standard_no_stem}.txt"])

    seen: set[Path] = set()
    matches: List[Path] = []
    for pattern in patterns:
        for path in text_dir.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                matches.append(path)

    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


@router.get("", response_model=APIResponse[StandardListResponse])
async def get_standards(
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    size: int = Query(10, ge=1, le=100, description="每页数量（1-100）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    department: Optional[str] = Query(None, description="按部门筛选"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取标准列表接口
    
    业务逻辑：
        1. 支持分页查询
        2. 支持关键词搜索（标准号、名称、描述）
        3. 支持按状态、部门、分类筛选
        4. 返回分页结果
    
    请求参数：
        - page: 页码（从 1 开始）
        - size: 每页数量（1-100）
        - search: 搜索关键词
        - status: 状态筛选
        - department: 部门筛选
        - category: 分类筛选
    
    返回数据：
        - data: 标准列表
        - total: 总记录数
        - page: 当前页码
        - size: 每页数量
        - pages: 总页数
    
    前端使用示例：
        const response = await api.getStandards({
            page: 1,
            size: 10,
            search: "航空",
            status: "有效"
        });
        const { data, total, pages } = response.data;
    
    注意事项：
        - 需要管理员权限
        - 搜索支持模糊匹配
        - 筛选条件可以组合使用
    
    Args:
        page: 页码
        size: 每页数量
        search: 搜索关键词
        status: 状态筛选
        department: 部门筛选
        category: 分类筛选
        db: 数据库会话
        current_user: 当前认证用户（管理员）
    
    Returns:
        APIResponse[StandardListResponse]: 分页的标准列表
    """
    # 构建查询
    query = db.query(Standard)
    
    # 关键词搜索（标准号、名称、描述）
    if search:
        query = query.filter(
            or_(
                Standard.standard_no.contains(search),
                Standard.name.contains(search),
                Standard.description.contains(search)
            )
        )
    
    # 筛选条件
    if status:
        query = query.filter(Standard.status == status)
    if department:
        query = query.filter(Standard.department == department)
    if category:
        query = query.filter(Standard.category == category)
    
    # 分页查询
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size if size > 0 else 0

    return APIResponse(
        data=StandardListResponse(
            data=[StandardResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    )


@router.get("/filter-options", response_model=APIResponse[Dict[str, List[str]]])
async def get_standard_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取标准筛选项（状态/部门/分类）。"""
    status_rows = db.query(Standard.status).filter(Standard.status.isnot(None)).distinct().all()
    dept_rows = db.query(Standard.department).filter(Standard.department.isnot(None)).distinct().all()
    category_rows = db.query(Standard.category).filter(Standard.category.isnot(None)).distinct().all()

    statuses = sorted({str(row[0]).strip() for row in status_rows if str(row[0]).strip()})
    departments = sorted({str(row[0]).strip() for row in dept_rows if str(row[0]).strip()})
    categories = sorted({str(row[0]).strip() for row in category_rows if str(row[0]).strip()})

    return APIResponse(
        data={
            "statuses": statuses,
            "departments": departments,
            "categories": categories,
        }
    )


@router.get("/{standard_id}/content", response_model=APIResponse[Dict[str, Any]])
async def get_standard_content(
    standard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取标准详情扩展内容（原文件可用性 + 解析文本预览）。"""
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_STANDARD_NOT_FOUND,
        )

    original_path = _find_original_upload_path(standard)
    text_path = _find_saved_text_path(standard)

    text_content = ""
    text_truncated = False
    text_length = 0
    max_chars = 20000
    if text_path is not None:
        raw = text_path.read_text(encoding="utf-8", errors="ignore")
        text_length = len(raw)
        if text_length > max_chars:
            text_content = raw[:max_chars]
            text_truncated = True
        else:
            text_content = raw

    return APIResponse(
        data={
            "standard_id": standard.id,
            "source_file": standard.source_file,
            "has_original_file": original_path is not None,
            "has_text_file": text_path is not None,
            "text_file_name": text_path.name if text_path is not None else None,
            "text_length": text_length,
            "text_truncated": text_truncated,
            "text_content": text_content,
        }
    )


@router.get("/{standard_id}/download")
async def download_standard_file(
    standard_id: int,
    kind: str = Query("original", description="下载类型：original|text"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载标准原文件或解析文本。"""
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_STANDARD_NOT_FOUND,
        )

    if kind not in {"original", "text"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="kind 仅支持 original 或 text",
        )

    if kind == "original":
        path = _find_original_upload_path(standard)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到可下载的原始文件",
            )
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        download_name = Path(standard.source_file or path.name).name
        return FileResponse(path=str(path), media_type=media_type, filename=download_name)

    path = _find_saved_text_path(standard)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到可下载的解析文本",
        )
    base = _sanitize_filename_fragment(standard.standard_no or standard.name or f"standard_{standard.id}")
    download_name = f"{base or f'standard_{standard.id}'}.txt"
    return FileResponse(path=str(path), media_type="text/plain; charset=utf-8", filename=download_name)


@router.get("/{standard_id}", response_model=APIResponse[StandardResponse])
async def get_standard(
    standard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取标准详情接口
    
    业务逻辑：
        1. 根据 ID 查询标准
        2. 返回标准详细信息
    
    请求参数：
        - standard_id: 标准 ID
    
    返回数据：
        - 标准的所有字段信息
        - 包括扩展字段（冲突状态、规则违反等）
    
    前端使用示例：
        const response = await api.getStandard(1);
        const standard = response.data;
        console.log(standard.name);
    
    错误处理：
        - 404: 标准不存在
    
    Args:
        standard_id: 标准 ID
        db: 数据库会话
        current_user: 当前认证用户（管理员）
    
    Returns:
        APIResponse[StandardResponse]: 标准详情
    """
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    
    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_STANDARD_NOT_FOUND
        )
    
    return APIResponse(data=StandardResponse.model_validate(standard))


@router.post("", response_model=APIResponse[StandardResponse], status_code=status.HTTP_201_CREATED)
async def create_standard(
    data: StandardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    创建标准接口
    
    业务逻辑：
        1. 检查标准号是否已存在
        2. 创建新标准
        3. 返回创建的标准
    
    请求参数：
        - standard_no: 标准号（必须唯一）
        - name: 标准名称
        - version: 版本号
        - status: 状态
        - category: 分类
        - department: 部门
        - description: 描述
    
    返回数据：
        - 创建的标准信息（包括生成的 ID）
    
    前端使用示例：
        const response = await api.createStandard({
            standard_no: "GB/T 12345-2020",
            name: "航空运输包装标准",
            version: "V2.1",
            status: "有效"
        });
        const standard = response.data;
    
    错误处理：
        - 400: 标准号已存在
    
    Args:
        data: 标准创建数据
        db: 数据库会话
        current_user: 当前认证用户（管理员）
    
    Returns:
        APIResponse[StandardResponse]: 创建的标准
    """
    # 检查标准号是否已存在
    existing = db.query(Standard).filter(
        Standard.standard_no == data.standard_no
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标准编号已存在"
        )
    
    # 创建标准
    standard = Standard(**data.model_dump())
    db.add(standard)
    db.commit()
    db.refresh(standard)
    try:
        _sync_vector_index(standard)
    except Exception as exc:
        logger.warning("标准 %s 向量索引同步失败: %s", standard.standard_no, exc)
    
    return APIResponse(
        data=StandardResponse.model_validate(standard),
        message="标准创建成功"
    )


@router.put("/{standard_id}", response_model=APIResponse[StandardResponse])
async def update_standard(
    standard_id: int,
    data: StandardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    更新标准接口
    
    业务逻辑：
        1. 查询标准是否存在
        2. 更新提供的字段
        3. 返回更新后的标准
    
    请求参数：
        - standard_id: 标准 ID
        - 需要更新的字段（可选）
    
    返回数据：
        - 更新后的标准信息
    
    前端使用示例：
        const response = await api.updateStandard(1, {
            name: "新的标准名称",
            status: "修订中"
        });
        const standard = response.data;
    
    错误处理：
        - 404: 标准不存在
    
    注意事项：
        - 只更新提供的字段
        - 不能更新标准号
    
    Args:
        standard_id: 标准 ID
        data: 标准更新数据
        db: 数据库会话
        current_user: 当前认证用户（管理员）
    
    Returns:
        APIResponse[StandardResponse]: 更新后的标准
    """
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    
    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_STANDARD_NOT_FOUND
        )
    
    # 更新字段（只更新提供的字段）
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(standard, field, value)
    
    db.commit()
    db.refresh(standard)
    try:
        _sync_vector_index(standard)
    except Exception as exc:
        logger.warning("标准 %s 向量索引同步失败: %s", standard.standard_no, exc)
    
    return APIResponse(
        data=StandardResponse.model_validate(standard),
        message="标准更新成功"
    )


@router.delete("/{standard_id}", response_model=APIResponse[None])
async def delete_standard(
    standard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    删除标准接口
    
    业务逻辑：
        1. 查询标准是否存在
        2. 删除标准
        3. 返回成功消息
    
    请求参数：
        - standard_id: 标准 ID
    
    返回数据：
        - 成功消息
    
    前端使用示例：
        await api.deleteStandard(1);
        console.log("标准删除成功");
    
    错误处理：
        - 404: 标准不存在
    
    注意事项：
        - 删除操作不可恢复
        - 建议先确认再删除
    
    Args:
        standard_id: 标准 ID
        db: 数据库会话
        current_user: 当前认证用户（管理员）
    
    Returns:
        APIResponse[None]: 成功消息
    """
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    
    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_STANDARD_NOT_FOUND
        )
    
    chunk_store = get_chunk_store()
    if chunk_store is not None:
        try:
            chunk_store.delete(
                {
                    "standard_id": standard.id,
                    "source": standard.source_file or f"{standard.standard_no}.txt",
                }
            )
        except Exception as exc:
            logger.warning("标准 %s 向量索引删除失败: %s", standard.standard_no, exc)

    db.delete(standard)
    db.commit()
    
    return APIResponse(message="标准删除成功")
