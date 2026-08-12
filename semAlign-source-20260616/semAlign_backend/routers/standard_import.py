"""标准导入路由 - 处理文件上传和数据导入"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session

from core.config import settings
from core.deps import get_db, get_current_admin_user, get_current_user
from models.user import User
from models.standard import Standard
from models.import_history import ImportHistory
from schemas.import_ import UploadResponse, ImportResponse
from schemas.standard import StandardCreate, StandardResponse
from schemas.base import APIResponse
from utils.document_processor import DocumentProcessor, get_chunk_store
from utils.pdf_parser import pdf_parser
from utils.validators import create_validator

router = APIRouter(prefix="/import", tags=["标准导入"])
logger = logging.getLogger(__name__)
_processor = DocumentProcessor()


def _build_file_id(
    *,
    standard_id: int | None = None,
    saved_filename: str | None = None,
    source_file: str | None = None,
) -> str:
    if standard_id is not None:
        return f"standard:{standard_id}"
    if saved_filename:
        return f"upload:{saved_filename}"
    if source_file:
        return f"source:{source_file}"
    return "unknown"


def _infer_source_file(record: Dict[str, Any]) -> str | None:
    source_file = record.get("source_file")
    if isinstance(source_file, str) and source_file.strip():
        return source_file.strip()
    saved = record.get("saved_filename")
    if isinstance(saved, str) and saved.strip():
        # 约定：YYYYmmdd_HHMMSS_originalName.ext
        parts = saved.split("_", 2)
        if len(parts) == 3 and parts[2].strip():
            return parts[2].strip()
        return saved.strip()
    return None


def _upsert_upload_vector_index(text: str, meta: Dict[str, str]) -> None:
    """上传解析后异步写入向量库，避免阻塞上传接口响应。"""
    try:
        chunk_store = get_chunk_store()
        if chunk_store is None:
            return
        chunk_count = chunk_store.upsert_text(text, meta=meta)
        logger.info("向量入库完成(后台): source=%s, chunks=%d", meta.get("source"), chunk_count)
    except Exception as exc:
        logger.warning("向量入库失败(后台): source=%s, error=%s", meta.get("source"), exc)


def _build_index_text(standard: Standard, extracted_text: str | None = None) -> str:
    if extracted_text and extracted_text.strip():
        return extracted_text
    parts = [
        standard.standard_no,
        standard.name,
        standard.version,
        standard.status,
        standard.category,
        standard.department or "",
        standard.description or "",
    ]
    return "\n".join(part for part in parts if part)


def _sync_standard_vector_index(
    standard: Standard,
    saved_filename: str | None = None,
    extracted_text: str | None = None,
) -> None:
    chunk_store = get_chunk_store()
    if chunk_store is None:
        return
    processor = DocumentProcessor()
    source_name = saved_filename or standard.source_file or f"{standard.standard_no}.txt"
    text = extracted_text or (processor.load_saved_text(source_name) if source_name else None)
    payload = _build_index_text(standard, text)
    chunk_store.upsert_text(
        payload,
        meta={
            "file_id": _build_file_id(
                standard_id=standard.id,
                saved_filename=saved_filename,
                source_file=standard.source_file,
            ),
            "standard_id": standard.id,
            "standard_no": standard.standard_no,
            "name": standard.name,
            "source": source_name,
            "source_file": standard.source_file,
        },
    )


@router.post("", response_model=APIResponse[List[StandardResponse]])
async def import_standards_batch(
    standards: List[StandardCreate],
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
) -> APIResponse[List[StandardResponse]]:
    """批量导入标准（与 mvp POST /api/import 一致，body 为标准对象数组）。"""
    imported: List[Standard] = []
    for std in standards:
        data = std.model_dump()
        existing = db.query(Standard).filter(
            Standard.standard_no == data["standard_no"]
        ).first()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
            db.add(existing)
            imported.append(existing)
        else:
            db_std = Standard(**data)
            db.add(db_std)
            imported.append(db_std)
    db.commit()
    for item in imported:
        db.refresh(item)
        try:
            _sync_standard_vector_index(item)
        except Exception as exc:
            logger.warning("标准 %s 向量索引同步失败: %s", item.standard_no, exc)
    return APIResponse(
        data=[StandardResponse.model_validate(x) for x in imported],
        message="批量导入完成",
    )


@router.post("/upload", response_model=APIResponse[UploadResponse])
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    文件上传接口
    
    业务逻辑：
        1. 验证文件类型（xlsx/xls/pdf）
        2. 验证文件大小（最大 20MB）
        3. 保存文件到服务器
        4. 解析并验证文件内容
        5. 返回验证结果
    
    请求参数：
        - file: 上传的文件（multipart/form-data）
    
    返回数据：
        - filename: 文件名
        - status: 上传状态
        - validation: 验证结果
            - total_rows: 总行数
            - valid_rows: 有效行数
            - need_update: 需要更新的行数
            - duplicate_rows: 重复行数
            - data: 验证后的数据
        - message: 消息说明
    
    前端使用示例：
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.uploadFile(formData);
        const { validation } = response.data;
        console.log(`有效行数：${validation.valid_rows}`);
    
    错误处理：
        - 400: 文件类型不支持
        - 413: 文件大小超限
        - 500: 文件解析失败
    
    注意事项：
        - 支持 Excel 和 PDF 文件
        - 文件保存到 data/uploads 目录
        - 验证结果可用于导入预览
    
    Args:
        file: 上传的文件
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[UploadResponse]: 上传响应
    """
    try:
        # 1. 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型：{file_ext}，请上传：{', '.join(settings.allowed_extensions)}"
            )
        
        # 2. 读取文件内容
        file_content = await file.read()
        
        # 3. 验证文件大小
        if len(file_content) > settings.max_upload_size:
            max_size_mb = settings.max_upload_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制（最大 {max_size_mb:.0f}MB）"
            )
        
        # 4. 确保上传目录存在
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 5. 保存文件到服务器
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 6. 按 xc 路径解析文件（DocumentProcessor 含 OCR）
        logger.info("开始解析上传文件(xc): name=%s, ext=%s, size=%d", file.filename, file_ext, len(file_content))
        parsed_text, images = await _processor.parse(file_content, file_ext, safe_filename)
        logger.info("xc 文档解析完成: name=%s, text_len=%d, images=%d", file.filename, len(parsed_text), len(images))

        # 7. 将解析文本写入向量库（后台任务，避免阻塞上传接口）
        if background_tasks is not None:
            background_tasks.add_task(
                _upsert_upload_vector_index,
                parsed_text,
                {
                    "file_id": _build_file_id(saved_filename=safe_filename, source_file=file.filename),
                    "source": file.filename,
                    "saved_as": safe_filename,
                    "uploaded_by": str(current_user.id),
                },
            )
        else:
            # 兜底：极少数情况下没有注入 BackgroundTasks
            _upsert_upload_vector_index(
                parsed_text,
                {
                    "file_id": _build_file_id(saved_filename=safe_filename, source_file=file.filename),
                    "source": file.filename,
                    "saved_as": safe_filename,
                    "uploaded_by": str(current_user.id),
                },
            )

        # 8. 标准信息提取：PDF 直接从 xc 抽取文本提取，Excel 仍按结构化解析
        if file_ext == ".pdf":
            records = pdf_parser.parse_text(parsed_text)
        else:
            records = await pdf_parser.parse(file_content, "excel", source_name=file.filename)
        logger.info("标准信息提取完成: name=%s, records=%d", file.filename, len(records))
        
        if not records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件中没有有效数据"
            )
        
        # 9. 验证数据
        for record in records:
            record["source_file"] = file.filename
            record["saved_filename"] = safe_filename
        validator = create_validator(db)
        validation_result = validator.validate_records(records)
        
        # 10. 返回上传和验证结果（返回完整数据,提交导入时可一次性入库）

        # 记录上传历史
        upload_history = ImportHistory(
            import_type="upload",
            filename=file.filename,
            saved_filename=safe_filename,
            status="success",
            success_count=validation_result['valid_rows'],
            failed_count=validation_result.get('invalid_rows', 0),
            user_id=current_user.id,
        )
        db.add(upload_history)
        db.commit()

        return APIResponse(
            data=UploadResponse(
                filename=file.filename,
                saved_filename=safe_filename,
                status="success",
                validation={
                    "total_rows": validation_result['total_rows'],
                    "valid_rows": validation_result['valid_rows'],
                    "need_update": validation_result['need_update'],
                    "duplicate_rows": validation_result['duplicate_rows'],
                    "invalid_rows": validation_result.get('invalid_rows', 0),
                    "data": validation_result['data']
                },
                message=f"文件解析成功，共 {validation_result['total_rows']} 条记录"
            )
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("上传文件解析失败(ValueError): name=%s, error=%s", file.filename, e)
        # 解析器对「无文本、无标准号、格式不符」等可预期问题抛 ValueError，应对客户端返回 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("上传文件处理失败: name=%s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件处理失败：{str(e)}"
        ) from e


_SKIP_IMPORT_KEYS = frozenset({"id", "created_at", "validation_status", "validation_error", "saved_filename"})


def _import_record_is_skipped(record: Dict[str, Any]) -> Optional[str]:
    if record.get("validation_status") in ["invalid", "duplicate"]:
        return record.get("validation_error", "无效记录")
    if not record.get("standard_no"):
        return "标准编号为空"
    return None


def _build_new_standard(record: Dict[str, Any]) -> Standard:
    return Standard(
        standard_no=record.get("standard_no"),
        name=record.get("name"),
        version=record.get("version"),
        status=record.get("status", "有效"),
        category=record.get("category", "未分类"),
        department=record.get("department"),
        description=record.get("description"),
        source_file=_infer_source_file(record),
        conflict_status=record.get("conflict_status", "无冲突"),
        rule_violations=record.get("rule_violations"),
    )


def _resolve_import_status(imported_count: int, updated_count: int, failed_count: int) -> str:
    if failed_count == 0:
        return "success"
    if imported_count > 0 or updated_count > 0:
        return "partial"
    return "failed"


def _process_import_record(
    db: Session,
    idx: int,
    record: Dict[str, Any],
) -> tuple[Optional[tuple[Standard, str | None, str | None]], Optional[str], str]:
    """
    处理单条导入记录。

    Returns:
        (indexed_entry, error_message, outcome) — outcome 为 skipped | updated | imported | error
    """
    skip_reason = _import_record_is_skipped(record)
    if skip_reason:
        return None, f"第 {idx} 行：{skip_reason}", "skipped"

    standard_no = record.get("standard_no")
    existing = db.query(Standard).filter(Standard.standard_no == standard_no).first()
    saved_filename = record.get("saved_filename")

    if existing:
        for key, value in record.items():
            if key not in _SKIP_IMPORT_KEYS:
                setattr(existing, key, value)
        if not existing.source_file:
            inferred_source = _infer_source_file(record)
            if inferred_source:
                existing.source_file = inferred_source
        existing.updated_at = datetime.now()
        db.add(existing)
        return (existing, saved_filename, None), None, "updated"

    new_standard = _build_new_standard(record)
    db.add(new_standard)
    return (new_standard, saved_filename, None), None, "imported"


def _record_import_outcome(
    outcome: str,
    *,
    idx: int,
    error_msg: str | None,
    entry: Optional[tuple[Standard, str | None, str | None]],
    counters: dict[str, int],
    errors: List[str],
    indexed_standards: List[tuple[Standard, str | None, str | None]],
) -> None:
    if outcome == "skipped":
        counters["failed"] += 1
        errors.append(error_msg or f"第 {idx} 行：无效记录")
        return
    if outcome == "updated":
        counters["updated"] += 1
    elif outcome == "imported":
        counters["imported"] += 1
    if entry is not None:
        indexed_standards.append(entry)


@router.post("/records", response_model=APIResponse[ImportResponse])
async def import_records(
    records: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    导入数据接口
    
    业务逻辑：
        1. 遍历记录列表
        2. 检查标准号是否已存在
        3. 存在则更新，不存在则插入
        4. 记录导入结果和错误
        5. 返回导入统计
    
    请求参数：
        - records: 待导入的记录列表
    
    返回数据：
        - imported_count: 成功导入的数量
        - updated_count: 成功更新的数量
        - failed_count: 导入失败的数量
        - errors: 错误信息列表
    
    前端使用示例：
        const response = await api.importRecords(records);
        const { imported_count, updated_count, failed_count, errors } = response.data;
        console.log(`成功导入：${imported_count} 条`);
        console.log(`成功更新：${updated_count} 条`);
        if (errors.length > 0) {
            console.error('导入错误：', errors);
        }
    
    注意事项：
        - 标准号重复的会更新
        - 失败的行会记录错误信息
        - 使用事务确保数据一致性
    
    Args:
        records: 待导入的记录列表
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[ImportResponse]: 导入响应
    """
    imported_count = 0
    updated_count = 0
    failed_count = 0
    errors: List[str] = []
    indexed_standards: List[tuple[Standard, str | None, str | None]] = []
    counters = {"imported": 0, "updated": 0, "failed": 0}
    
    try:
        for idx, record in enumerate(records, 1):
            try:
                entry, error_msg, outcome = _process_import_record(db, idx, record)
                _record_import_outcome(
                    outcome,
                    idx=idx,
                    error_msg=error_msg,
                    entry=entry,
                    counters=counters,
                    errors=errors,
                    indexed_standards=indexed_standards,
                )
            except Exception as e:
                counters["failed"] += 1
                errors.append(f"第 {idx} 行：{str(e)}")

        imported_count = counters["imported"]
        updated_count = counters["updated"]
        failed_count = counters["failed"]

        # 提交事务
        db.commit()

        import_history = ImportHistory(
            import_type="batch",
            filename=None,
            saved_filename=None,
            status=_resolve_import_status(imported_count, updated_count, failed_count),
            success_count=imported_count + updated_count,
            failed_count=failed_count,
            error_message="; ".join(errors[:5]) if errors else None,  # 只保存前5条错误
            user_id=current_user.id,
        )
        db.add(import_history)
        db.commit()

        for standard, saved_filename, extracted_text in indexed_standards:
            db.refresh(standard)
            try:
                _sync_standard_vector_index(standard, saved_filename=saved_filename, extracted_text=extracted_text)
            except Exception as exc:
                logger.warning("标准 %s 向量索引同步失败: %s", standard.standard_no, exc)
                errors.append(f"标准 {standard.standard_no} 向量索引同步失败：{exc}")
        
        return APIResponse(
            data=ImportResponse(
                imported_count=imported_count,
                updated_count=updated_count,
                failed_count=failed_count,
                errors=errors
            ),
            message=f"导入完成：新增 {imported_count} 条，更新 {updated_count} 条，失败 {failed_count} 条"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入失败：{str(e)}"
        )


@router.get("/history", response_model=APIResponse[Dict[str, Any]])
async def get_import_history(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    获取导入历史记录列表

    Args:
        page: 页码（从 1 开始）
        size: 每页数量（1-100）
        db: 数据库会话
        current_user: 当前用户

    Returns:
        APIResponse: 包含导入历史记录列表和分页信息
    """
    try:
        # 查询总数
        total = db.query(ImportHistory).count()

        # 分页查询
        offset = (page - 1) * size
        histories = (
            db.query(ImportHistory)
            .order_by(ImportHistory.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # 转换为字典
        data = []
        for h in histories:
            data.append({
                "id": h.id,
                "import_type": h.import_type,
                "filename": h.filename,
                "saved_filename": h.saved_filename,
                "status": h.status,
                "success_count": h.success_count,
                "failed_count": h.failed_count,
                "error_message": h.error_message,
                "user_id": h.user_id,
                "username": h.user.username if h.user else None,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            })

        return APIResponse(
            data={
                "data": data,
                "total": total,
                "page": page,
                "size": size,
            },
            message="查询成功"
        )

    except Exception as e:
        logger.error(f"查询导入历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败：{str(e)}"
        )
