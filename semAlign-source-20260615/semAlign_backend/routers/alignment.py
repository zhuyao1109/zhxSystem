"""标准对齐路由 - 处理标准语义对齐任务"""

from types import SimpleNamespace
from typing import Any, List
from pathlib import Path
import re
import sqlite3
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.database import SessionLocal
from pydantic import BaseModel
from datetime import datetime

from core.config import settings
from core.deps import get_db, get_current_admin_user, get_current_user
from models.user import User
from models.alignment_task import AlignmentTask
from models.standard import Standard
from schemas.alignment import (
    AlignmentReviewRequest,
    AlignmentTaskCreate,
    AlignmentTaskResponse,
    AlignmentTaskListResponse
)
from schemas.base import APIResponse
from services.alignment_executor import run_alignment, _load_standard_text
from utils.document_processor import DocumentProcessor, get_chunk_store
from utils.pdf_parser import DEFAULT_STD_NAME

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

router = APIRouter(prefix="/alignment", tags=["标准对齐"])
logger = logging.getLogger(__name__)

MSG_TASK_NOT_FOUND = "任务不存在"


class AlignmentChatRequest(BaseModel):
    """对齐聊天请求"""

    message: str
    group1_id: str | None = None
    group2_id: str | None = None


class AlignmentChatResponse(BaseModel):
    """对齐聊天响应"""

    answer: str
    references: list[str]


class ManualMappingRequest(BaseModel):
    """手动映射请求"""

    conflict_id: str
    decision: str  # "accept" | "reject" | "modify"
    modified_recommendation: str | None = None
    notes: str | None = None


class ManualMappingResponse(BaseModel):
    """手动映射响应"""

    conflict_id: str
    decision: str
    updated_at: str


def _clean_text_for_chat(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _build_chat_context_from_target(target: Any, max_chars: int = 1600) -> tuple[str, str]:
    standard_no = str(getattr(target, "standard_no", "") or "").strip()
    name = str(getattr(target, "name", "") or "").strip()
    text = _load_standard_text(target)
    text = _clean_text_for_chat(text)
    excerpt = text[:max_chars] if text else ""
    label = f"{standard_no}《{name}》".strip("《》")
    if not label:
        label = name or standard_no or DEFAULT_STD_NAME
    return label, excerpt


def _build_alignment_chat_llm() -> tuple[Any | None, str]:
    """
    Create OpenAI-compatible LLM client for alignment chat.
    Priority:
      1) FOURZ_API_KEY/FOURZ_API_BASE/FOURZ_API_MODEL
      2) DEEPSEEK_API_KEY (+ default deepseek base/model)
    """
    if OpenAI is None:
        return None, ""

    fourz_key = (settings.fourz_api_key or "").strip()
    if fourz_key:
        base = (settings.fourz_api_base or "").strip() or None
        model = (settings.fourz_api_model or "").strip() or "gpt-4o-mini"
        return OpenAI(api_key=fourz_key, base_url=base), model

    deepseek_key = (settings.deepseek_api_key or "").strip()
    if deepseek_key:
        base = (settings.deepseek_api_base or "").strip() or "https://api.deepseek.com/v1"
        model = (settings.deepseek_api_model or "").strip() or "deepseek-chat"
        return OpenAI(api_key=deepseek_key, base_url=base), model

    return None, ""


def _extract_chat_keywords(message: str) -> list[str]:
    """从用户问题中提取可用于标准库检索的关键词。"""
    core = _extract_chat_query(message)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", core or message or "").strip()
    if not normalized:
        return []
    tokens = [tok.strip() for tok in normalized.split() if len(tok.strip()) >= 2]
    if not tokens and core:
        tokens = [core.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(token)
    return deduped[:8]


_CHAT_GREETING_TOKENS = frozenset({
    "你好", "您好", "hello", "hi", "hey", "在吗", "早上好", "下午好", "晚上好",
})
_CHAT_FILLER_PATTERNS = (
    r"请问",
    r"你知道",
    r"你了解",
    r"可以告诉",
    r"能不能",
    r"能否",
    r"什么是",
    r"是什么",
    r"介绍一下",
    r"帮我",
    r"吗$",
    r"呢$",
    r"啊$",
    r"呀$",
)


def _extract_chat_query(message: str) -> str:
    """去掉寒暄与客套用语，提取真正用于检索的问题核心。"""
    text = (message or "").strip()
    for pattern in _CHAT_FILLER_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text).strip()
    tokens = [
        token
        for token in normalized.split()
        if token and token.lower() not in _CHAT_GREETING_TOKENS
    ]
    return " ".join(tokens).strip()


def _is_pure_greeting_message(message: str) -> bool:
    """仅当消息不含实质问题时视为纯问候。"""
    return not _extract_chat_query(message)


def _query_standard_blocks_for_chat(
    message: str, db: Session, max_blocks: int
) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    refs: list[str] = []
    keywords = _extract_chat_keywords(message) or [message.strip()]
    filters = []
    for keyword in keywords:
        filters.extend(
            [
                Standard.standard_no.contains(keyword),
                Standard.name.contains(keyword),
                Standard.description.contains(keyword),
                Standard.category.contains(keyword),
                Standard.source_file.contains(keyword),
            ]
        )
    hits = (
        db.query(Standard)
        .filter(or_(*filters))
        .order_by(Standard.updated_at.desc())
        .limit(max_blocks)
        .all()
    )
    for idx, item in enumerate(hits, start=1):
        label = f"{item.standard_no}《{item.name}》"
        desc = _clean_text_for_chat(item.description or "该标准暂无详细描述")
        refs.append(label)
        blocks.append(f"[检索标准{idx}] {label}\n{desc[:1200]}")
    return blocks, refs


def _append_vector_blocks_for_chat(
    message: str, remaining: int, blocks: list[str], refs: list[str]
) -> None:
    if remaining <= 0:
        return
    chunk_store = get_chunk_store()
    if chunk_store is None:
        return
    try:
        for idx, hit in enumerate(chunk_store.retrieve(message, top_k=remaining), start=1):
            text = _clean_text_for_chat(str(hit.get("page_content") or ""))
            if not text:
                continue
            meta = hit.get("metadata") or {}
            source = str(meta.get("source_file") or meta.get("source") or "向量库文档")
            ref = Path(source).name or source
            refs.append(ref)
            blocks.append(f"[向量片段{idx}] {ref}\n{text[:1200]}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("alignment chat retrieval failed: %s", exc)


def _dedupe_refs_preserve_order(refs: list[str]) -> list[str]:
    dedup_refs: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        dedup_refs.append(ref)
    return dedup_refs


def _build_chat_retrieval_context(message: str, db: Session, max_blocks: int = 5) -> tuple[list[str], list[str]]:
    """为未选择标准时的小助手构造标准库/向量库上下文。"""
    query = _extract_chat_query(message) or message.strip()
    blocks, refs = _query_standard_blocks_for_chat(query, db, max_blocks)
    remaining = max_blocks - len(blocks)
    _append_vector_blocks_for_chat(query, remaining, blocks, refs)
    return blocks, _dedupe_refs_preserve_order(refs)


def _run_alignment_task_background(task_id: int) -> None:
    """后台执行对齐任务，避免创建任务接口长时间阻塞。"""
    db = SessionLocal()
    try:
        task = db.query(AlignmentTask).filter(AlignmentTask.id == task_id).first()
        if task is None:
            logger.warning("对齐后台任务不存在: task_id=%s", task_id)
            return

        options = task.options or {}
        group1_id = str(options.get("group1Id", "")).strip()
        group2_id = str(options.get("group2Id", "")).strip()
        task.status = "processing"
        task.result_json = {
            "message": "对齐任务正在后台执行",
            "group1_id": group1_id,
            "group2_id": group2_id,
        }
        task.completed_at = None
        db.commit()

        try:
            std_left = _resolve_alignment_target(group1_id, db)
            std_right = _resolve_alignment_target(group2_id, db)
            catalog = [
                {
                    "id": s.id,
                    "standard_no": s.standard_no,
                    "name": s.name,
                    "status": s.status,
                    "description": s.description or "",
                    "category": s.category,
                }
                for s in db.query(Standard).filter(Standard.is_active == True).all()  # noqa: E712
            ]
            result = run_alignment(
                std_left,
                std_right,
                options=options,
                standards_catalog=catalog,
            )
            task.result_json = result
            task.status = "completed"
            task.review_status = "draft"
            task.completed_at = int(datetime.now().timestamp())
            db.add(task)
            db.commit()
        except ValueError as exc:
            task.status = "failed"
            task.result_json = {
                "error": str(exc),
                "group1_id": group1_id,
                "group2_id": group2_id,
            }
            task.completed_at = int(datetime.now().timestamp())
            db.add(task)
            db.commit()
            logger.warning("对齐任务参数或文本无效: task_id=%s, error=%s", task_id, exc)
        except Exception as exc:
            task.status = "failed"
            task.result_json = {
                "error": str(exc),
                "group1_id": group1_id,
                "group2_id": group2_id,
            }
            task.completed_at = int(datetime.now().timestamp())
            db.add(task)
            db.commit()
            logger.exception("对齐任务后台执行失败: task_id=%s", task_id)
    finally:
        db.close()


def _validate_alignment_target_value(raw_value: Any) -> str:
    if raw_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少标准组ID，请先在前端选择两个文档。",
        )

    value = str(raw_value).strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标准组ID不能为空。",
        )
    return value


def _list_vector_chunk_hits(chunk_store: Any, source: str) -> list[Any]:
    hits = chunk_store.list_chunks({"source": source}, limit=1)
    if not hits:
        hits = chunk_store.list_chunks({"source_file": source}, limit=1)
    return hits


def _chroma_sqlite_has_embedding_source(source: str) -> bool:
    project_root = Path(__file__).resolve().parents[1]
    chroma_dir = Path(settings.chroma_db_dir)
    if not chroma_dir.is_absolute():
        chroma_dir = (project_root / chroma_dir).resolve()
    db_path = chroma_dir / "chroma.sqlite3"
    if not db_path.exists():
        return False

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        row = cur.execute(
            """
            select 1
            from embedding_metadata
            where key in ('source','source_file') and string_value=?
            limit 1
            """,
            (source,),
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


def _resolve_vector_alignment_target(source: str) -> Any:
    processor = DocumentProcessor()
    saved_text = processor.load_saved_text(source)
    chunk_store = get_chunk_store()
    hits: list[Any] = []
    if chunk_store is not None:
        hits = _list_vector_chunk_hits(chunk_store, source)
    sqlite_has_source = False
    if not hits:
        sqlite_has_source = _chroma_sqlite_has_embedding_source(source)
    # 兜底：向量能力不可用时允许从已保存文本继续对齐
    if not hits and saved_text is None and not sqlite_has_source:
        if chunk_store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="向量检索能力未启用或初始化失败，且未找到对应文本缓存，无法创建对齐任务。",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"向量文档不存在：{source}",
        )
    return SimpleNamespace(
        id=None,
        standard_no=f"VECTOR::{source}",
        name=source,
        description=f"向量库文档：{source}",
        source_file=source,
    )


def _resolve_db_standard_target(sid: int, db: Session) -> Standard:
    standard = db.query(Standard).filter(Standard.id == sid).first()
    if standard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"待对齐标准不存在：{sid}",
        )
    return standard


def _resolve_alignment_target(raw_value: Any, db: Session) -> Any:
    value = _validate_alignment_target_value(raw_value)

    if value.startswith("vector:"):
        source = value.split(":", 1)[1].strip()
        if not source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="向量文档标识无效。",
            )
        return _resolve_vector_alignment_target(source)

    try:
        sid = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标准组ID格式错误。",
        ) from exc

    return _resolve_db_standard_target(sid, db)


@router.post("/tasks", response_model=APIResponse[AlignmentTaskResponse], status_code=status.HTTP_201_CREATED)
async def create_alignment_task(
    data: AlignmentTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建对齐任务接口
    
    业务逻辑：
        1. 接收对齐请求（文本 + 选项）
        2. 创建任务记录（状态：pending）
        3. 加入处理队列（异步）
        4. 返回任务信息
    
    请求参数：
        - text: 待对齐的文本内容
        - options: 对齐选项（可选）
            - mode: 对齐模式（strict/loose）
            - language: 语言（zh/en）
    
    返回数据：
        - 任务信息
            - id: 任务 ID
            - user_id: 创建用户 ID
            - input_text: 输入文本
            - status: 任务状态
            - created_at: 创建时间
    
    前端使用示例：
        const response = await api.createAlignmentTask({
            text: "GB/T 12345-2020 与 ISO 9001:2015 的对比",
            options: { mode: "strict" }
        });
        const task = response.data;
        console.log(`任务 ID：${task.id}`);
    
    注意事项：
        - 任务异步处理
        - 结果需要轮询或使用 WebSocket 获取
        - options 为可选，使用默认配置
    
    Args:
        data: 对齐任务创建数据
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[AlignmentTaskResponse]: 创建的任务
    """
    options = data.options or {}
    group1_id = str(options.get("group1Id", "")).strip()
    group2_id = str(options.get("group2Id", "")).strip()
    if not group1_id or not group2_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少标准组ID，请先在前端选择两个文档。",
        )
    if group1_id == group2_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择两个不同的标准。",
        )
    # 创建任务前只做目标存在性校验；实际执行放到后台任务，避免接口阻塞。
    _resolve_alignment_target(group1_id, db)
    _resolve_alignment_target(group2_id, db)

    task = AlignmentTask(
        user_id=current_user.id,
        input_text=data.text,
        options=data.options,
        status="pending",
        result_json={
            "message": "对齐任务已创建，等待后台执行",
            "group1_id": group1_id,
            "group2_id": group2_id,
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(_run_alignment_task_background, task.id)

    return APIResponse(
        data=AlignmentTaskResponse.model_validate(task),
        message="对齐任务已创建，请轮询任务状态"
    )


@router.get("/tasks", response_model=APIResponse[AlignmentTaskListResponse])
async def get_alignment_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取对齐任务列表接口
    
    业务逻辑：
        1. 查询当前用户的任务
        2. 支持分页
        3. 按创建时间倒序
        4. 返回任务列表
    
    请求参数：
        - page: 页码（从 1 开始）
        - size: 每页数量（1-100）
    
    返回数据：
        - data: 任务列表
            - id: 任务 ID
            - input_text: 输入文本
            - status: 任务状态
            - created_at: 创建时间
            - completed_at: 完成时间
        - total: 总任务数
        - page: 当前页码
        - size: 每页数量
    
    前端使用示例：
        const response = await api.getAlignmentTasks({ page: 1, size: 10 });
        const { data, total, pages } = response.data;
        data.forEach(task => {
            console.log(task.status);
        });
    
    注意事项：
        - 只返回当前用户的任务
        - 结果按创建时间倒序
    
    Args:
        page: 页码
        size: 每页数量
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[AlignmentTaskListResponse]: 任务列表
    """
    # 管理员可管理全部任务，普通用户仅查看自己的任务
    query = db.query(AlignmentTask)
    if current_user.role != "admin":
        query = query.filter(AlignmentTask.user_id == current_user.id)
    
    # 分页查询
    total = query.count()
    tasks = query.order_by(AlignmentTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return APIResponse(
        data=AlignmentTaskListResponse(
            data=[AlignmentTaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            size=size
        )
    )


@router.get("/tasks/{task_id}", response_model=APIResponse[AlignmentTaskResponse])
async def get_alignment_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取对齐任务详情接口
    
    业务逻辑：
        1. 查询任务是否存在
        2. 检查任务是否属于当前用户
        3. 返回任务详情和结果
    
    请求参数：
        - task_id: 任务 ID
    
    返回数据：
        - 任务信息
            - id: 任务 ID
            - input_text: 输入文本
            - status: 任务状态
            - result_json: 对齐结果（完成后才有）
            - created_at: 创建时间
            - completed_at: 完成时间
    
    前端使用示例：
        const response = await api.getAlignmentTask(1);
        const task = response.data;
        if (task.status === "completed") {
            console.log(task.result_json);
        }
    
    错误处理：
        - 404: 任务不存在
    
    注意事项：
        - 只能查看自己的任务
        - result_json 只有状态为 completed 时才有值
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[AlignmentTaskResponse]: 任务详情
    """
    # 查询任务
    query = db.query(AlignmentTask).filter(AlignmentTask.id == task_id)
    if current_user.role != "admin":
        query = query.filter(AlignmentTask.user_id == current_user.id)
    task = query.first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_TASK_NOT_FOUND
        )
    
    return APIResponse(data=AlignmentTaskResponse.model_validate(task))


def _apply_review_submit(task: AlignmentTask, current_user: User, notes: str | None) -> None:
    if task.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能提交自己的对齐任务")
    if task.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务未完成，不能提交审核")
    task.review_status = "submitted"
    task.review_notes = notes


def _apply_review_approve(
    task: AlignmentTask, current_user: User, notes: str | None, now: datetime
) -> None:
    task.review_status = "approved"
    task.reviewed_by = current_user.id
    task.reviewed_at = now
    task.review_notes = notes


def _apply_review_reject(
    task: AlignmentTask, current_user: User, notes: str | None, now: datetime
) -> None:
    task.review_status = "rejected"
    task.reviewed_by = current_user.id
    task.reviewed_at = now
    task.review_notes = notes


def _apply_review_publish(
    task: AlignmentTask, current_user: User, notes: str | None, now: datetime
) -> None:
    if task.review_status not in {"approved", "published"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先审核通过后再发布")
    task.review_status = "published"
    task.reviewed_by = current_user.id
    task.reviewed_at = task.reviewed_at or now
    task.published_at = now
    task.review_notes = notes or task.review_notes


def _apply_admin_review_action(
    task: AlignmentTask, action: str, current_user: User, notes: str | None, now: datetime
) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    if action == "approve":
        _apply_review_approve(task, current_user, notes, now)
    elif action == "reject":
        _apply_review_reject(task, current_user, notes, now)
    else:
        _apply_review_publish(task, current_user, notes, now)


@router.post("/tasks/{task_id}/review", response_model=APIResponse[AlignmentTaskResponse])
async def review_alignment_task(
    task_id: int,
    data: AlignmentReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[AlignmentTaskResponse]:
    """提交/审核/发布对齐结果。"""
    task = db.query(AlignmentTask).filter(AlignmentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TASK_NOT_FOUND)

    action = data.action.strip().lower()
    now = datetime.now()
    if action == "submit":
        _apply_review_submit(task, current_user, data.notes)
    elif action in {"approve", "reject", "publish"}:
        _apply_admin_review_action(task, action, current_user, data.notes, now)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的审核动作")

    db.commit()
    db.refresh(task)
    return APIResponse(data=AlignmentTaskResponse.model_validate(task), message="状态已更新")


@router.get("/published", response_model=APIResponse[AlignmentTaskListResponse])
async def get_published_alignment_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通用户查看管理员已发布的标准对齐结果。"""
    query = db.query(AlignmentTask).filter(
        AlignmentTask.status == "completed",
        AlignmentTask.review_status == "published",
    )
    total = query.count()
    tasks = query.order_by(AlignmentTask.published_at.desc(), AlignmentTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return APIResponse(
        data=AlignmentTaskListResponse(
            data=[AlignmentTaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            size=size,
        )
    )


@router.post("/tasks/{task_id}/save", response_model=APIResponse[None])
async def save_alignment_result(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[None]:
    """保存对齐结果（如收藏）；演示实现不落库扩展表。"""
    task = db.query(AlignmentTask).filter(
        AlignmentTask.id == task_id,
        AlignmentTask.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_TASK_NOT_FOUND,
        )
    return APIResponse(data=None, message="已保存")


@router.post("/tasks/{task_id}/manual-mapping", response_model=APIResponse[ManualMappingResponse])
async def save_manual_mapping(
    task_id: int,
    data: ManualMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    保存手动映射决策接口

    业务逻辑：
        1. 查询任务是否存在
        2. 检查任务是否属于当前用户
        3. 更新任务结果中的冲突决策
        4. 保存用户的手动决策（接受/拒绝/修改）
        5. 返回更新结果

    请求参数：
        - task_id: 任务 ID
        - conflict_id: 冲突 ID
        - decision: 决策类型（accept/reject/modify）
        - modified_recommendation: 修改后的建议（decision=modify时必填）
        - notes: 备注说明（可选）

    返回数据：
        - conflict_id: 冲突 ID
        - decision: 决策类型
        - updated_at: 更新时间

    前端使用示例：
        const response = await api.saveManualMapping(taskId, {
            conflict_id: "conflict-1",
            decision: "accept",
            notes: "同意系统建议"
        });

    错误处理：
        - 404: 任务不存在
        - 400: 冲突ID不存在

    注意事项：
        - 只能修改自己的任务
        - 决策会保存在任务的 result_json 中

    Args:
        task_id: 任务 ID
        data: 手动映射请求数据
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        APIResponse[ManualMappingResponse]: 映射响应
    """
    # 查询任务
    task = db.query(AlignmentTask).filter(
        AlignmentTask.id == task_id,
        AlignmentTask.user_id == current_user.id,
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_TASK_NOT_FOUND,
        )

    # 获取任务结果
    result_json = task.result_json or {}
    conflicts = result_json.get("conflicts", [])

    # 查找对应的冲突
    conflict_found = False
    for conflict in conflicts:
        if conflict.get("id") == data.conflict_id:
            conflict_found = True
            # 保存手动决策
            if "manual_decision" not in conflict:
                conflict["manual_decision"] = {}

            conflict["manual_decision"]["decision"] = data.decision
            conflict["manual_decision"]["user_id"] = current_user.id
            conflict["manual_decision"]["username"] = current_user.username
            conflict["manual_decision"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if data.modified_recommendation:
                conflict["manual_decision"]["modified_recommendation"] = data.modified_recommendation

            if data.notes:
                conflict["manual_decision"]["notes"] = data.notes

            break

    if not conflict_found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"冲突ID不存在：{data.conflict_id}",
        )

    # 更新任务结果
    task.result_json = result_json
    db.commit()

    return APIResponse(
        data=ManualMappingResponse(
            conflict_id=data.conflict_id,
            decision=data.decision,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
        message="手动决策已保存"
    )


@router.post("/tasks/{task_id}/retry", response_model=APIResponse[AlignmentTaskResponse])
async def retry_alignment_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重新执行对齐任务接口

    业务逻辑：
        1. 查询原任务是否存在
        2. 检查任务是否属于当前用户
        3. 使用原任务的参数重新执行对齐
        4. 更新任务状态和结果
        5. 返回更新后的任务信息

    请求参数：
        - task_id: 任务 ID

    返回数据：
        - 更新后的任务信息

    前端使用示例：
        const response = await api.retryAlignmentTask(1);
        const task = response.data;
        console.log("重新对齐成功");

    错误处理：
        - 404: 任务不存在
        - 400: 任务参数无效

    注意事项：
        - 只能重新执行自己的任务
        - 会覆盖原有的对齐结果

    Args:
        task_id: 任务 ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        APIResponse[AlignmentTaskResponse]: 更新后的任务
    """
    # 查询任务
    task = db.query(AlignmentTask).filter(
        AlignmentTask.id == task_id,
        AlignmentTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_TASK_NOT_FOUND
        )

    # 获取原任务的参数
    options = task.options or {}
    group1_id = str(options.get("group1Id", "")).strip()
    group2_id = str(options.get("group2Id", "")).strip()

    if not group1_id or not group2_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务参数不完整，无法重新执行"
        )

    # 解析标准
    try:
        _resolve_alignment_target(group1_id, db)
        _resolve_alignment_target(group2_id, db)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析标准失败：{exc}"
        ) from exc

    # 更新任务状态为待后台重新执行
    task.status = "pending"
    task.result_json = {
        "message": "对齐任务已重新提交，等待后台执行",
        "group1_id": group1_id,
        "group2_id": group2_id,
    }
    task.completed_at = None
    db.commit()
    db.refresh(task)

    _run_alignment_task_background(task.id)
    db.refresh(task)

    return APIResponse(
        data=AlignmentTaskResponse.model_validate(task),
        message="重新对齐已完成"
    )


@router.delete("/tasks/{task_id}", response_model=APIResponse[None])
async def delete_alignment_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除对齐任务接口

    业务逻辑：
        1. 查询任务是否存在
        2. 检查任务是否属于当前用户
        3. 删除任务
        4. 返回成功消息

    请求参数：
        - task_id: 任务 ID

    返回数据：
        - 成功消息

    前端使用示例：
        await api.deleteAlignmentTask(1);
        console.log("任务删除成功");

    错误处理：
        - 404: 任务不存在

    注意事项：
        - 只能删除自己的任务
        - 删除操作不可恢复

    Args:
        task_id: 任务 ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        APIResponse[None]: 成功消息
    """
    # 查询任务
    task = db.query(AlignmentTask).filter(
        AlignmentTask.id == task_id,
        AlignmentTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_TASK_NOT_FOUND
        )

    # 删除任务
    db.delete(task)
    db.commit()

    return APIResponse(message="任务删除成功")


def _try_build_target_context_blocks(
    group1_id: str | None, group2_id: str | None, db: Session
) -> tuple[list[str], list[str]]:
    target_refs: list[str] = []
    context_blocks: list[str] = []
    if not (group1_id and group2_id):
        return target_refs, context_blocks
    try:
        left = _resolve_alignment_target(group1_id, db)
        right = _resolve_alignment_target(group2_id, db)
        for idx, item in enumerate([left, right], start=1):
            label, excerpt = _build_chat_context_from_target(item)
            target_refs.append(label)
            if excerpt:
                context_blocks.append(f"[标准{idx}] {label}\n{excerpt}")
    except HTTPException:
        # 聊天场景下不强制中断，转为标准库检索增强
        pass
    return target_refs, context_blocks


def _build_alignment_chat_user_prompt(message: str, context_blocks: list[str]) -> str:
    if context_blocks:
        return (
            f"用户问题：{message}\n\n"
            f"可用上下文：\n{chr(10).join(context_blocks)}\n\n"
            "请结合上下文回答。若问题涉及两个标准的对齐，请尽量输出：\n"
            "1) 关键差异\n2) 可能冲突\n3) 优先级建议\n4) 执行建议\n5) 依据来源"
        )
    return (
        f"用户问题：{message}\n\n"
        "当前没有选定标准，也没有检索到直接上下文。"
        "请作为标准对齐 AI 助手，给出有帮助的通用解释或操作建议；"
        "如果用户只是问候，请自然回应并提示可以选择两个标准后进一步分析。"
    )


def _try_llm_alignment_chat(
    message: str, context_blocks: list[str], target_refs: list[str]
) -> tuple[APIResponse[AlignmentChatResponse] | None, str]:
    llm_client, llm_model = _build_alignment_chat_llm()
    if llm_client is None:
        return None, ""
    try:
        sys_prompt = (
            "你是 SemAlign 标准对齐系统中的 AI 助手，熟悉标准管理、标准检索、"
            "条款对齐、冲突识别、优先级规则和人工审核流程。请用中文回答。"
            "当提供了标准上下文时，优先基于上下文回答并引用依据；"
            "当没有足够上下文时，可以给出通用方法建议，但必须明确说明没有检索到直接证据。"
            "回答要专业、清晰、可执行。"
        )
        user_prompt = _build_alignment_chat_user_prompt(message, context_blocks)
        resp = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        answer = (resp.choices[0].message.content or "").strip()
        if answer:
            return (
                APIResponse(
                    data=AlignmentChatResponse(answer=answer, references=target_refs)
                ),
                "",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("alignment chat LLM call failed, fallback to rule reply: %s", exc)
        hint = ""
        err = str(exc)
        if "401" in err or "Invalid token" in err:
            hint = "（提示：当前配置的大模型 API Key 无效或已过期，请更新 .env 中的 FOURZ_API_KEY 或 DEEPSEEK_API_KEY。）"
        return None, hint
    return None, ""


def _alignment_chat_use_llm() -> bool:
    mode = (settings.alignment_chat_mode or "vector_engine").strip().lower()
    if mode == "llm":
        return True
    if mode == "vector_engine":
        return False
    # auto：配置了 LLM Key 时走大模型，否则走向量检索
    client, _ = _build_alignment_chat_llm()
    return client is not None


_BUILTIN_TERM_BRIEFS: dict[str, str] = {
    "osi": (
        "OSI（Open Systems Interconnection，开放系统互连参考模型）是 ISO/IEC 7498 定义的网络通信分层模型，"
        "共分为七层：物理层、数据链路层、网络层、传输层、会话层、表示层、应用层。"
        "它是理论参考模型，用于描述不同系统之间如何分层交互；实际工程里互联网更常用 TCP/IP。"
        "在民航信息系统集成中，理解 OSI 分层有助于梳理接口协议、数据交换边界与安全域划分。"
    ),
    "osi协议": (
        "OSI 协议通常指基于 OSI 七层参考模型的一系列通信协议族（如 X.25、CLNP 等）。"
        "日常所说的「OSI 模型」更多指分层架构本身，而非单一协议。"
        "若你在做标准对齐，请说明具体引用了哪份标准/条款，我可以结合文档做条款级比对。"
    ),
    "tcp ip": (
        "TCP/IP 是互联网事实上的四层协议栈（网络接口层、网络层、传输层、应用层），"
        "与 OSI 七层模型在概念上可对应，但分层粒度不同。"
    ),
}


def _filter_relevant_context_blocks(blocks: list[str], query: str) -> list[str]:
    """过滤与问题关键词无关的检索片段，避免低质量向量命中误导回答。"""
    keywords = _extract_chat_keywords(query)
    if not keywords:
        return blocks
    lowered_keys = [kw.lower() for kw in keywords if len(kw) >= 2]
    if not lowered_keys:
        return blocks
    relevant: list[str] = []
    for block in blocks:
        haystack = block.lower()
        if any(key in haystack for key in lowered_keys):
            relevant.append(block)
    return relevant


def _filter_relevant_chat_context(
    blocks: list[str], refs: list[str], query: str
) -> tuple[list[str], list[str]]:
    if not blocks:
        return blocks, refs
    keywords = _extract_chat_keywords(query)
    if not keywords:
        return blocks, refs
    lowered_keys = [kw.lower() for kw in keywords if len(kw) >= 2]
    if not lowered_keys:
        return blocks, refs
    filtered_blocks: list[str] = []
    filtered_refs: list[str] = []
    for idx, block in enumerate(blocks):
        haystack = block.lower()
        if any(key in haystack for key in lowered_keys):
            filtered_blocks.append(block)
            if idx < len(refs):
                filtered_refs.append(refs[idx])
    return filtered_blocks, _dedupe_refs_preserve_order(filtered_refs)


def _lookup_builtin_term_brief(query: str) -> str | None:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", (query or "").lower()).strip()
    if not normalized:
        return None
    if normalized in _BUILTIN_TERM_BRIEFS:
        return _BUILTIN_TERM_BRIEFS[normalized]
    for key, brief in _BUILTIN_TERM_BRIEFS.items():
        if key in normalized or normalized in key:
            return brief
    return None


def _format_context_block_for_answer(block: str, max_len: int = 320) -> str:
    header, _, body = block.partition("\n")
    label = header.strip("[]") or "相关片段"
    snippet = _clean_text_for_chat(body)[:max_len]
    return f"**{label}**\n{snippet}"


def _build_vector_engine_chat_response(
    message: str,
    context_blocks: list[str],
    target_refs: list[str],
    llm_unavailable_hint: str = "",
) -> APIResponse[AlignmentChatResponse]:
    """无大模型时，基于标准库 + 向量库检索结果生成回答。"""
    if context_blocks:
        sections = [
            _format_context_block_for_answer(block)
            for block in context_blocks[:4]
        ]
        answer = (
            f"针对你的问题「{message}」，我在标准库/向量库中找到 {len(context_blocks)} 条相关依据：\n\n"
            + "\n\n".join(sections)
            + "\n\n如需对两个标准做条款级差异与冲突分析，请在页面选择 **标准组 1** 和 **标准组 2** 后继续提问。"
        )
        if llm_unavailable_hint:
            answer += f"\n\n{llm_unavailable_hint}"
        return APIResponse(
            data=AlignmentChatResponse(answer=answer, references=target_refs)
        )

    if _is_pure_greeting_message(message):
        answer = (
            "你好！我是 SemAlign 标准对齐助手。\n"
            "我可以帮你分析标准冲突、解释条款含义、提供对齐建议。"
            "请直接提问，或在页面选择两个标准组后让我做差异分析。"
        )
        return APIResponse(data=AlignmentChatResponse(answer=answer, references=[]))

    topic = _extract_chat_query(message) or message
    builtin = _lookup_builtin_term_brief(topic)
    if builtin:
        answer = (
            f"关于「{topic}」，标准库中暂未检索到直接条款，以下是通用背景说明（非项目内标准原文）：\n\n"
            f"{builtin}\n\n"
            "如需基于你们已导入的标准做对齐，请上传文档或选择标准组后继续提问。"
        )
        if llm_unavailable_hint:
            answer += f"\n\n{llm_unavailable_hint}"
        return APIResponse(data=AlignmentChatResponse(answer=answer, references=[]))

    answer = (
        f"关于「{topic}」，目前在标准库和向量库中 **未检索到直接相关的条款片段**。\n"
        "可能原因：相关标准尚未导入，或问题与现有文档语义匹配度较低。\n"
        "建议：\n"
        "1. 在「标准导入」上传相关 PDF/Excel；\n"
        "2. 在页面上选择两个标准组后提问；\n"
        "3. 如需大模型自由问答，请配置有效的 FOURZ_API_KEY 或 DEEPSEEK_API_KEY，"
        "并将 ALIGNMENT_CHAT_MODE 设为 auto 或 llm。"
    )
    if llm_unavailable_hint:
        answer += f"\n\n{llm_unavailable_hint}"
    return APIResponse(data=AlignmentChatResponse(answer=answer, references=[]))


def _build_rule_fallback_chat_response(
    message: str,
    db: Session,
    context_blocks: list[str] | None = None,
    target_refs: list[str] | None = None,
) -> APIResponse[AlignmentChatResponse]:
    if context_blocks:
        return _build_vector_engine_chat_response(message, context_blocks, target_refs or [])

    keywords = _extract_chat_keywords(message) or [message]
    filters = []
    for keyword in keywords:
        filters.extend(
            [
                Standard.standard_no.contains(keyword),
                Standard.name.contains(keyword),
                Standard.description.contains(keyword),
            ]
        )
    hits = (
        db.query(Standard)
        .filter(or_(*filters))
        .order_by(Standard.updated_at.desc())
        .limit(3)
        .all()
    )

    if not hits:
        return _build_vector_engine_chat_response(message, [], [])

    refs = [f"{item.standard_no}《{item.name}》" for item in hits]
    snippets = []
    for item in hits:
        desc = (item.description or "该标准暂无详细描述").strip()
        snippets.append(f"{item.standard_no}：{desc[:90]}")

    answer = (
        f"基于你的问题「{message}」，我在标准库中找到 {len(hits)} 条相关标准。"
        "建议先对齐这些标准中的术语定义与判定口径：\n- "
        + "\n- ".join(snippets)
    )

    return APIResponse(
        data=AlignmentChatResponse(answer=answer, references=refs)
    )


@router.post("/chat", response_model=APIResponse[AlignmentChatResponse])
async def chat_alignment_assistant(
    data: AlignmentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """对齐助手聊天接口（llm 模式优先大模型；vector_engine 模式基于向量+标准库检索）。"""
    message = (data.message or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息不能为空",
        )

    target_refs, context_blocks = _try_build_target_context_blocks(
        data.group1_id, data.group2_id, db
    )

    if not context_blocks:
        retrieval_blocks, retrieval_refs = _build_chat_retrieval_context(message, db)
        context_blocks.extend(retrieval_blocks)
        target_refs.extend(retrieval_refs)

    query_topic = _extract_chat_query(message) or message
    context_blocks, target_refs = _filter_relevant_chat_context(
        context_blocks, target_refs, query_topic
    )

    if not _alignment_chat_use_llm():
        return _build_vector_engine_chat_response(message, context_blocks, target_refs)

    llm_response, llm_hint = _try_llm_alignment_chat(message, context_blocks, target_refs)
    if llm_response is not None:
        return llm_response

    return _build_vector_engine_chat_response(
        message, context_blocks, target_refs, llm_unavailable_hint=llm_hint
    )
