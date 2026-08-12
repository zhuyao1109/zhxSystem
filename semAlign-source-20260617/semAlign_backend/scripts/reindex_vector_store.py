"""从当前标准库重建本地向量索引。"""

from __future__ import annotations

from core.database import SessionLocal
from models.standard import Standard
from utils.document_processor import ChunkStore, DocumentProcessor, vector_store_is_available


def main() -> None:
    if not vector_store_is_available():
        raise SystemExit("向量检索依赖或本地模型不可用，无法重建索引")

    db = SessionLocal()
    try:
        standards = db.query(Standard).all()
        processor = DocumentProcessor()
        store = ChunkStore(force_rebuild=True)
        total_chunks = 0

        for standard in standards:
            text = processor.load_saved_text(standard.source_file) if standard.source_file else None
            if not text:
                text = "\n".join(
                    part
                    for part in [
                        standard.standard_no,
                        standard.name,
                        standard.version,
                        standard.status,
                        standard.category,
                        standard.department or "",
                        standard.description or "",
                    ]
                    if part
                )
            total_chunks += store.upsert_text(
                text,
                meta={
                    "file_id": f"standard:{standard.id}",
                    "standard_id": standard.id,
                    "standard_no": standard.standard_no,
                    "name": standard.name,
                    "source": standard.source_file or f"{standard.standard_no}.txt",
                    "source_file": standard.source_file,
                },
            )

        print(f"已完成重建：{len(standards)} 条标准，{total_chunks} 个 chunks")
    finally:
        db.close()


if __name__ == "__main__":
    main()
