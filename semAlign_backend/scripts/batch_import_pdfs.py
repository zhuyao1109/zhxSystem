"""从本地 PDF 目录批量导入标准库与向量索引。"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# 须在 document_processor 导入前设置，否则默认离线模式会导致向量模型加载失败
os.environ.setdefault("HF_HUB_OFFLINE", "0")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import SessionLocal
from models.import_history import ImportHistory
from models.standard import Standard
from models.user import User
from utils.document_processor import DocumentProcessor, get_chunk_store, vector_store_is_available
from utils.pdf_parser import pdf_parser

logger = logging.getLogger(__name__)


def _pick_pdfs(
    pdf_dir: Path,
    *,
    limit: int | None,
    include: list[str] | None,
    skip_existing: bool,
) -> tuple[list[Path], list[str]]:
    if include:
        files = [pdf_dir / name for name in include]
        return [f for f in files if f.is_file()], []

    db = SessionLocal()
    try:
        existing_sources = {
            row[0]
            for row in db.query(Standard.source_file).filter(Standard.source_file.isnot(None)).all()
            if row[0]
        }
    finally:
        db.close()

    skipped: list[str] = []
    candidates: list[Path] = []
    for f in sorted(pdf_dir.glob("*.pdf")):
        if skip_existing and f.name in existing_sources:
            skipped.append(f.name)
            continue
        candidates.append(f)

    if limit is not None and limit > 0:
        candidates = candidates[:limit]
    return candidates, skipped


async def _import_one(
    pdf_path: Path,
    *,
    upload_dir: Path,
    processor: DocumentProcessor,
    chunk_store,
    user_id: int,
) -> dict:
    filename = pdf_path.name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    saved_path = upload_dir / saved_filename
    shutil.copy2(pdf_path, saved_path)

    file_bytes = pdf_path.read_bytes()
    parsed_text, _ = await processor.parse(file_bytes, ".pdf", saved_filename)
    records = pdf_parser.parse_text(parsed_text)
    if not records:
        raise ValueError("未能从 PDF 提取标准信息")

    record = records[0]
    record["source_file"] = filename
    record["saved_filename"] = saved_filename
    if not record.get("description"):
        from utils.text_cleaner import summarize_standard_text

        record["description"] = summarize_standard_text(parsed_text)

    db = SessionLocal()
    try:
        standard_no = record.get("standard_no")
        if not standard_no:
            raise ValueError("标准号为空")

        existing = db.query(Standard).filter(Standard.standard_no == standard_no).first()
        if existing:
            for key in ("name", "version", "status", "category", "department", "description", "source_file"):
                value = record.get(key)
                if value not in (None, ""):
                    setattr(existing, key, value)
            standard = existing
            action = "updated"
        else:
            standard = Standard(
                standard_no=standard_no,
                name=record.get("name") or filename,
                version=record.get("version") or "V1.0",
                status=record.get("status") or "有效",
                category=record.get("category") or "未分类",
                department=record.get("department"),
                description=record.get("description"),
                source_file=filename,
            )
            db.add(standard)
            action = "imported"

        db.flush()

        chunks = 0
        if chunk_store is not None and parsed_text.strip():
            chunks = chunk_store.upsert_text(
                parsed_text,
                meta={
                    "file_id": f"standard:{standard.id}",
                    "standard_id": standard.id,
                    "standard_no": standard.standard_no,
                    "name": standard.name,
                    "source": filename,
                    "source_file": filename,
                    "saved_as": saved_filename,
                    "uploaded_by": str(user_id),
                },
            )

        history = ImportHistory(
            import_type="batch_pdf",
            filename=filename,
            saved_filename=saved_filename,
            status="success",
            success_count=1,
            failed_count=0,
            user_id=user_id,
        )
        db.add(history)
        db.commit()
        db.refresh(standard)

        return {
            "action": action,
            "filename": filename,
            "standard_no": standard.standard_no,
            "name": standard.name,
            "chunks": chunks,
            "text_len": len(parsed_text),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def run_batch(
    pdf_dir: Path,
    *,
    limit: int | None,
    include: list[str] | None,
    skip_existing: bool,
    log_file: Path | None,
) -> None:
    upload_dir = PROJECT_ROOT / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    if not vector_store_is_available():
        logger.warning("向量模型不可用，将仅写入标准库")

    import utils.document_processor as dp

    dp._chunk_store_instance = None
    chunk_store = get_chunk_store()
    processor = DocumentProcessor()
    files, skipped = _pick_pdfs(pdf_dir, limit=limit, include=include, skip_existing=skip_existing)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == "admin").first() or db.query(User).first()
        if not user:
            raise SystemExit("未找到用户，请先运行 scripts/init_user.py")
        user_id = user.id
    finally:
        db.close()

    def log(msg: str) -> None:
        print(msg, flush=True)
        if log_file:
            with log_file.open("a", encoding="utf-8") as fh:
                fh.write(msg + "\n")

    total = len(files)
    log(f"开始批量导入: 待处理 {total} 个, 跳过已存在 {len(skipped)} 个, 来源 {pdf_dir}")
    ok, failed = [], []
    started = time.time()

    for idx, pdf_path in enumerate(files, start=1):
        try:
            result = await _import_one(
                pdf_path,
                upload_dir=upload_dir,
                processor=processor,
                chunk_store=chunk_store,
                user_id=user_id,
            )
            ok.append(result)
            log(
                f"[{idx}/{total}] ✓ [{result['action']}] {result['standard_no']} | "
                f"{result['filename']} | chunks={result['chunks']}"
            )
        except Exception as exc:
            failed.append((pdf_path.name, str(exc)))
            log(f"[{idx}/{total}] ✗ {pdf_path.name}: {exc}")

    elapsed = time.time() - started
    log(
        f"\n完成: 成功 {len(ok)}, 失败 {len(failed)}, 跳过 {len(skipped)}, "
        f"耗时 {elapsed/60:.1f} 分钟"
    )
    if chunk_store is not None:
        log(f"BM25 chunks: {len(chunk_store._all_chunks)}")
    if failed:
        log("\n失败列表:")
        for name, err in failed:
            log(f"  - {name}: {err}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="批量导入 PDF 到标准库与向量索引")
    parser.add_argument("--pdf-dir", type=Path, default=PROJECT_ROOT.parent / "pdf")
    parser.add_argument("--limit", type=int, default=10, help="导入数量上限，0 表示不限制")
    parser.add_argument("--all", action="store_true", help="导入目录下全部 PDF（等同 --limit 0）")
    parser.add_argument("--no-skip-existing", action="store_true", help="不跳过 source_file 已入库的文件")
    parser.add_argument("--files", nargs="*", help="指定文件名列表")
    parser.add_argument(
        "--log-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "batch_import.log",
        help="进度日志文件",
    )
    args = parser.parse_args()

    if not args.pdf_dir.exists():
        raise SystemExit(f"PDF 目录不存在: {args.pdf_dir}")

    limit = 0 if args.all else args.limit
    if limit == 0:
        limit = None

    if args.log_file:
        args.log_file.write_text(
            f"=== batch import started {datetime.now().isoformat()} ===\n",
            encoding="utf-8",
        )

    asyncio.run(
        run_batch(
            args.pdf_dir,
            limit=limit,
            include=args.files or None,
            skip_existing=not args.no_skip_existing,
            log_file=args.log_file,
        )
    )


if __name__ == "__main__":
    main()
