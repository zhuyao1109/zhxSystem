"""文档处理器单元测试（不加载真实向量模型）。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from utils.document_processor import (
    ChunkStore,
    DocumentProcessor,
    _append_unused_ocr_lines,
    _find_image_caption,
    _is_junk_image,
    get_chunk_store,
)


class TestOcrHelpers:
    def test_find_image_caption(self):
        class Rect:
            x0 = 10
            y1 = 100
            x1 = 200

        ocr_lines = [
            {
                "used": False,
                "box": [[100, 110], [180, 110], [180, 130], [100, 130]],
                "text": "图1 示例说明",
            },
        ]
        caption, idx = _find_image_caption(ocr_lines, Rect(), 1.0, 1.0)
        assert caption == "图1 示例说明"
        assert idx == 0

    def test_append_unused_ocr_lines(self):
        lines = [{"used": False, "box": [[0, 5]], "text": "未使用行"}]
        elements: list[dict] = []
        _append_unused_ocr_lines(lines, elements)
        assert elements[0]["content"] == "未使用行"

    def test_is_junk_image_uniform(self):
        from PIL import Image

        img = Image.new("L", (50, 50), color=128)
        assert _is_junk_image(img) is True

    def test_is_junk_image_too_small(self):
        from PIL import Image

        img = Image.new("L", (10, 10), color=0)
        assert _is_junk_image(img) is True


class TestChunkStoreRetrieve:
    def test_retrieve_falls_back_to_semantic_on_ensemble_error(self):
        store = ChunkStore.__new__(ChunkStore)
        store._all_chunks = [MagicMock(page_content="chunk", metadata={})]

        semantic_doc = MagicMock(page_content="语义命中", metadata={"source_file": "a.pdf"})
        semantic_ret = MagicMock()
        semantic_ret.invoke.return_value = [semantic_doc]
        store._vectorstore = MagicMock()
        store._vectorstore.as_retriever.return_value = semantic_ret

        with patch("utils.document_processor.BM25Retriever.from_documents", side_effect=AttributeError("no id")):
            hits = store.retrieve("信息安全", top_k=2)

        assert len(hits) == 1
        assert hits[0]["page_content"] == "语义命中"

    def test_doc_matches_and_build_where(self):
        store = ChunkStore.__new__(ChunkStore)
        assert store._doc_matches({"standard_id": "1"}, {"standard_id": "1"})
        assert not store._doc_matches({"standard_id": "1"}, {"standard_id": "2"})
        assert store._build_where({"file_id": "standard:1"}) == {"file_id": "standard:1"}

    def test_list_chunks_from_bm25_cache(self):
        store = ChunkStore.__new__(ChunkStore)
        doc = MagicMock()
        doc.page_content = "条款内容"
        doc.metadata = {"standard_id": "9"}
        store._all_chunks = [doc]
        hits = store.list_chunks({"standard_id": "9"}, limit=5)
        assert hits[0]["page_content"] == "条款内容"

    def test_fetch_chunks_from_vectorstore(self):
        store = ChunkStore.__new__(ChunkStore)
        store._vectorstore = MagicMock()
        store._vectorstore._collection.get.return_value = {
            "documents": ["向量文档"],
            "metadatas": [{"source_file": "b.pdf"}],
        }
        hits = store._fetch_chunks_from_vectorstore({"standard_id": "1"}, 10)
        assert hits[0]["page_content"] == "向量文档"

    def test_delete_skips_when_no_meta_keys(self):
        store = ChunkStore.__new__(ChunkStore)
        store._vectorstore = MagicMock()
        store._all_chunks = []
        store._bm25_pkl = MagicMock()
        store.delete({})

    def test_delete_with_meta(self, tmp_path):
        store = ChunkStore.__new__(ChunkStore)
        store._vectorstore = MagicMock()
        store._all_chunks = [MagicMock(metadata={"standard_id": "1"})]
        store._bm25_pkl = tmp_path / "bm25.pkl"
        store._bm25_pkl.parent.mkdir(parents=True, exist_ok=True)
        with patch.object(store, "_save_bm25_chunks"):
            store.delete({"standard_id": "1"})
        store._vectorstore._collection.delete.assert_called()

    def test_upsert_text(self, tmp_path):
        store = ChunkStore.__new__(ChunkStore)
        store._splitter = MagicMock()
        store._splitter.split.return_value = ["第一段文本", "第二段文本"]
        store._vectorstore = MagicMock()
        store._all_chunks = []
        store._bm25_pkl = tmp_path / "bm25.pkl"
        store._bm25_pkl.parent.mkdir(parents=True, exist_ok=True)
        doc_cls = MagicMock(side_effect=lambda page_content, metadata: MagicMock(
            page_content=page_content, metadata=metadata
        ))
        with (
            patch("utils.document_processor.Document", doc_cls),
            patch.object(store, "delete"),
            patch.object(store, "_save_bm25_chunks"),
        ):
            count = store.upsert_text("x " * 80, meta={"standard_id": "9"})
        assert count == 2
        assert store._vectorstore.add_documents.called

    def test_fetch_chunks_vectorstore_error_fallback(self):
        store = ChunkStore.__new__(ChunkStore)
        store._vectorstore = MagicMock()
        store._vectorstore._collection.get.side_effect = RuntimeError("db")
        assert store._fetch_chunks_from_vectorstore({"x": 1}, 5) == []

    def test_get_chunk_store_unavailable(self, monkeypatch):
        monkeypatch.setattr("utils.document_processor.vector_store_is_available", lambda: False)
        import utils.document_processor as dp

        dp._chunk_store_instance = None
        assert get_chunk_store() is None

    def test_vector_store_is_available(self):
        from utils.document_processor import vector_store_is_available

        assert isinstance(vector_store_is_available(), bool)


class TestDocumentProcessorHelpers:
    def test_needs_ocr_fallback(self):
        processor = DocumentProcessor.__new__(DocumentProcessor)
        assert not processor._needs_ocr_fallback("这是一段正常的中文标准文本。" * 5)
        assert processor._needs_ocr_fallback("")

    def test_save_and_load_text(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.document_processor.settings.text_output_dir", str(tmp_path))
        processor = DocumentProcessor()
        path = processor._save_text("测试正文", "demo.pdf")
        assert path.exists()
        loaded = processor.load_saved_text("demo.pdf")
        assert loaded == "测试正文"
