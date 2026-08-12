"""向量数据库概览路由 - 提供 Chroma 库内容的只读展示。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.config import settings
from core.deps import get_current_admin_user
from models.user import User
from schemas.base import APIResponse

router = APIRouter(prefix="/vector-store", tags=["向量数据库"])


class VectorSourceRow(BaseModel):
    source: str
    saved_as: str | None = None
    chunk_count: int


class VectorStoreOverviewData(BaseModel):
    available: bool
    db_path: str
    collection_name: str | None = None
    dimension: int | None = None
    total_chunks: int = 0
    total_sources: int = 0
    rows: list[VectorSourceRow]


@router.get("/overview", response_model=APIResponse[VectorStoreOverviewData])
async def get_vector_store_overview(
    current_user: User = Depends(get_current_admin_user),
):
    project_root = Path(__file__).resolve().parents[1]
    chroma_dir = Path(settings.chroma_db_dir)
    if not chroma_dir.is_absolute():
        chroma_dir = (project_root / chroma_dir).resolve()
    db_path = chroma_dir / "chroma.sqlite3"

    if not db_path.exists():
        return APIResponse(
            data=VectorStoreOverviewData(
                available=False,
                db_path=str(db_path),
                rows=[],
            )
        )

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        collection_row = cur.execute(
            "select name, dimension from collections limit 1"
        ).fetchone()
        total_chunks = cur.execute("select count(*) from embeddings").fetchone()[0] or 0
        total_sources = cur.execute(
            "select count(distinct string_value) from embedding_metadata where key='source'"
        ).fetchone()[0] or 0

        rows = cur.execute(
            """
            select
              src.string_value as source,
              save.string_value as saved_as,
              count(*) as chunk_count
            from embedding_metadata src
            left join embedding_metadata save
              on save.id = src.id and save.key = 'saved_as'
            where src.key = 'source'
            group by src.string_value, save.string_value
            order by chunk_count desc, src.string_value asc
            limit 20
            """
        ).fetchall()

        return APIResponse(
            data=VectorStoreOverviewData(
                available=True,
                db_path=str(db_path),
                collection_name=collection_row["name"] if collection_row else None,
                dimension=collection_row["dimension"] if collection_row else None,
                total_chunks=total_chunks,
                total_sources=total_sources,
                rows=[
                    VectorSourceRow(
                        source=row["source"],
                        saved_as=row["saved_as"],
                        chunk_count=row["chunk_count"],
                    )
                    for row in rows
                ],
            )
        )
    except sqlite3.Error:
        return APIResponse(
            data=VectorStoreOverviewData(
                available=False,
                db_path=str(db_path),
                rows=[],
            )
        )
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
