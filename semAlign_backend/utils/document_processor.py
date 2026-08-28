"""文档抽取与本地向量检索工具。

组成：
    DocumentProcessor — PDF/Excel 解析、OCR 回退、向量入库；
    ChunkStore — BM25 + Chroma 混合检索封装；
    辅助解析器 _OCRPdfParser / _ExcelParser / _ImageAwareSplitter。
"""

from __future__ import annotations

import io
import logging
import os
import pickle
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber

from core.config import settings

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

logger = logging.getLogger(__name__)

try:
    import fitz  # type: ignore
    from PIL import Image, ImageStat
    from rapidocr_onnxruntime import RapidOCR

    _OCR_OK = True
except ImportError:
    fitz = None
    Image = None
    ImageStat = None
    RapidOCR = None
    _OCR_OK = False

try:
    from langchain.schema import Document
    from langchain.retrievers import EnsembleRetriever
    from langchain_chroma import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.retrievers import BM25Retriever
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    _LANGCHAIN_OK = True
except ImportError:
    Document = Any  # type: ignore
    _LANGCHAIN_OK = False


# ---------------------------------------------------------------------------
# 图片与 OCR 辅助
# ---------------------------------------------------------------------------

def _is_junk_image(pil_img: "Image.Image") -> bool:
    if ImageStat is None:
        return True
    width, height = pil_img.size
    if width < settings.ocr_min_image_size and height < settings.ocr_min_image_size:
        return True
    ratio = max(width, height) / max(min(width, height), 1)
    if ratio > 8:
        return True
    gray = pil_img.convert("L")
    stddev = ImageStat.Stat(gray).stddev[0]
    if stddev < settings.ocr_min_stddev:
        return True
    lo, hi = gray.getextrema()
    return lo == hi


_CAPTION_PATTERN = re.compile(r"图\s?\d+|Fig(ure)?\s?\.?\s?\d+", re.IGNORECASE)


def _find_image_caption(
    ocr_lines: List[Dict[str, Any]],
    img_rect: Any,
    scale_x: float,
    scale_y: float,
) -> Tuple[str, int]:
    caption = ""
    caption_idx = -1
    best_dist = 100
    for line_idx, line in enumerate(ocr_lines):
        if line["used"]:
            continue
        box = line["box"]
        text = line["text"]
        text_top_y = box[0][1] / scale_y
        text_mid_x = ((box[0][0] + box[1][0]) / 2) / scale_x
        if (
            text_top_y > img_rect.y1
            and text_top_y - img_rect.y1 < best_dist
            and img_rect.x0 - 20 < text_mid_x < img_rect.x1 + 20
            and _CAPTION_PATTERN.search(text)
        ):
            caption = text
            caption_idx = line_idx
            break
    return caption, caption_idx


def _append_unused_ocr_lines(
    ocr_lines: List[Dict[str, Any]],
    page_elements: List[Dict[str, Any]],
) -> None:
    for line in ocr_lines:
        if not line["used"]:
            page_elements.append({"y": line["box"][0][1], "content": line["text"]})


class _OCRPdfParser:
    _ocr: Optional["RapidOCR"] = None

    @classmethod
    def _get_ocr(cls) -> "RapidOCR":
        if not _OCR_OK or RapidOCR is None:
            raise ImportError("OCR 依赖未安装")
        if cls._ocr is None:
            cls._ocr = RapidOCR()
        return cls._ocr

    def parse_bytes(
        self,
        file_bytes: bytes,
        image_out_dir: Optional[str] = None,
        max_pages: Optional[int] = None,
        dpi: Optional[int] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            return self._parse_file(tmp_path, image_out_dir, max_pages=max_pages, dpi=dpi)
        finally:
            os.unlink(tmp_path)

    def _extract_page_image(
        self,
        doc: Any,
        page: Any,
        img_idx: int,
        img_meta: Tuple[Any, ...],
        ocr_lines: List[Dict[str, Any]],
        scale_x: float,
        scale_y: float,
        image_out_dir: Optional[str],
        all_images: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        xref = img_meta[0]
        try:
            base_image = doc.extract_image(xref)
            pil_img = Image.open(io.BytesIO(base_image["image"]))
            if _is_junk_image(pil_img):
                return None
            img_rects = page.get_image_rects(xref)
            if not img_rects:
                return None
            img_rect = img_rects[0]

            caption, caption_idx = _find_image_caption(ocr_lines, img_rect, scale_x, scale_y)
            if caption_idx < 0:
                return None
            ocr_lines[caption_idx]["used"] = True

            img_filename = f"page{page.number + 1}_img{img_idx}.{base_image['ext']}"
            img_path: Optional[str] = None
            if image_out_dir:
                os.makedirs(image_out_dir, exist_ok=True)
                img_path = os.path.join(image_out_dir, img_filename)
                pil_img.save(img_path)

            all_images.append(
                {
                    "filename": img_filename,
                    "full_path": img_path,
                    "page": page.number + 1,
                    "caption": caption,
                    "size": pil_img.size,
                }
            )
            return {
                "y": img_rect.y0 * scale_y,
                "content": (
                    "\n--- 图片开始 ---\n"
                    f"[文件: {img_filename}]\n"
                    f"[标题: {caption}]\n"
                    f"[尺寸: {pil_img.size[0]}x{pil_img.size[1]}]\n"
                    "--- 图片结束 ---\n"
                ),
            }
        except Exception as exc:
            logger.warning("PDF 图片抽取失败: %s", exc)
            return None

    def _process_page(
        self,
        doc: Any,
        page: Any,
        dpi: Optional[int],
        image_out_dir: Optional[str],
        all_images: List[Dict[str, Any]],
    ) -> Optional[str]:
        pix = page.get_pixmap(dpi=dpi or settings.ocr_dpi)
        img_bytes = pix.tobytes("png")
        ocr_results, _ = self._get_ocr()(img_bytes)
        ocr_lines = [{"box": r[0], "text": r[1], "used": False} for r in (ocr_results or [])]

        page_elements: List[Dict[str, Any]] = []
        scale_y = pix.height / page.rect.height
        scale_x = pix.width / page.rect.width

        for img_idx, img_meta in enumerate(page.get_images(full=True), start=1):
            element = self._extract_page_image(
                doc,
                page,
                img_idx,
                img_meta,
                ocr_lines,
                scale_x,
                scale_y,
                image_out_dir,
                all_images,
            )
            if element is not None:
                page_elements.append(element)

        _append_unused_ocr_lines(ocr_lines, page_elements)
        if not page_elements:
            return None
        page_elements.sort(key=lambda item: item["y"])
        return "\n".join(item["content"] for item in page_elements)

    def _parse_file(
        self,
        filepath: str,
        image_out_dir: Optional[str] = None,
        max_pages: Optional[int] = None,
        dpi: Optional[int] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        if fitz is None or Image is None:
            raise ImportError("OCR 依赖未安装")

        doc = fitz.open(filepath)
        total_pages = len(doc)
        all_page_texts: List[str] = []
        all_images: List[Dict[str, Any]] = []

        for page in doc:
            if max_pages is not None and page.number >= max_pages:
                break
            page_text = self._process_page(doc, page, dpi, image_out_dir, all_images)
            if page_text:
                all_page_texts.append(page_text)

        doc.close()
        if max_pages is not None and total_pages > max_pages:
            logger.info("OCR 快速模式: 仅处理前 %d/%d 页", max_pages, total_pages)
        return "\n\n".join(all_page_texts), all_images


class _ExcelParser:
    def parse_bytes(self, file_bytes: bytes) -> str:
        df = pd.read_excel(io.BytesIO(file_bytes))
        lines: List[str] = []
        for _, row in df.iterrows():
            parts = []
            for col in df.columns:
                value = row[col]
                if pd.notna(value):
                    parts.append(f"{col}: {str(value).strip()}")
            if parts:
                lines.append(" | ".join(parts))
        if not lines:
            raise ValueError("Excel 文件中没有有效数据")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 文档解析主类（PDF / Excel）
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """标准文档解析器（PDF / Excel）。

    职责：
        - PDF：pdfplumber 文本层优先，必要时 RapidOCR 限页回退；
        - Excel：转为文本行或结构化行供导入校验；
        - 输出纯文本路径与可选图片元数据列表。

    典型调用方：
        routers/standard_import 上传解析流程。
    """

    def __init__(self) -> None:
        self.text_output_dir = Path(settings.text_output_dir)
        self.image_output_dir = Path(settings.image_output_dir)
        self._ocr_parser = _OCRPdfParser()
        self._excel_parser = _ExcelParser()

    async def parse(
        self,
        file_bytes: bytes,
        file_ext: str,
        saved_filename: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        ext = file_ext.lower().lstrip(".")
        images: List[Dict[str, Any]] = []

        if ext == "pdf":
            # 快路径：优先走文本层提取，避免对可提取 PDF 全页 OCR 导致耗时过长
            text = self._extract_pdf_text(file_bytes)
            if text.strip() and not self._needs_ocr_fallback(text):
                logger.info("PDF 命中文本层，跳过 OCR: %s", saved_filename)
            elif _OCR_OK:
                try:
                    # 上传导入场景优先快速返回：OCR 仅扫描前若干页抓取标准号，避免前端超时
                    quick_max_pages = getattr(settings, "upload_ocr_max_pages", 3)
                    quick_dpi = getattr(settings, "upload_ocr_dpi", 160)
                    text, images = self._ocr_parser.parse_bytes(
                        file_bytes,
                        str(self.image_output_dir / Path(saved_filename).stem),
                        max_pages=quick_max_pages,
                        dpi=quick_dpi,
                    )
                    logger.info("PDF 触发 OCR 回退成功: %s", saved_filename)
                except Exception as exc:
                    logger.warning("OCR 解析失败，沿用文本层结果: %s", exc)
            else:
                logger.warning("OCR 依赖不可用，且文本层为空或乱码: %s", saved_filename)
        elif ext in ("xlsx", "xls"):
            text = self._excel_parser.parse_bytes(file_bytes)
        else:
            raise ValueError(f"不支持的文件类型: .{ext}")

        if not text.strip():
            raise ValueError("文件中没有可提取的文本内容")

        from utils.text_cleaner import clean_parsed_text

        text = clean_parsed_text(text)
        if not text.strip():
            raise ValueError("文件中没有可提取的文本内容")

        self._save_text(text, saved_filename)
        return text, images

    def _extract_pdf_text(self, file_bytes: bytes) -> str:
        texts: List[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
        return "\n".join(texts)

    def _needs_ocr_fallback(self, text: str) -> bool:
        """
        参考 xc 体系中的 OCR 判定：文本层存在但编码崩坏时仍应强制 OCR。
        """
        sample = text[:5000]
        # GB 标准文档常见编码崩坏特征字
        garbled_markers = ("犌", "犅", "犜", "犐", "犆", "犛", "犃", "犇", "")
        if any(marker in sample for marker in garbled_markers):
            return True

        # 文本中可读中文比例过低时，视作可疑（避免“看起来有字，实际不可用”）
        visible_chars = re.sub(r"\s+", "", sample)
        if not visible_chars:
            return True
        cjk = re.findall(r"[\u4e00-\u9fff]", visible_chars)
        cjk_ratio = len(cjk) / max(len(visible_chars), 1)

        # 若包含标准关键字但中文占比极低，通常是乱码/错码文本层
        has_std_hint = any(k in sample.upper() for k in ("GB/T", "MH/T", "ISO", "标准"))
        if has_std_hint and cjk_ratio < 0.02:
            return True

        return False

    def _save_text(self, text: str, original_filename: str) -> Path:
        self.text_output_dir.mkdir(parents=True, exist_ok=True)
        txt_path = self.text_output_dir / f"{Path(original_filename).stem}.txt"
        txt_path.write_text(text, encoding="utf-8")
        return txt_path

    def get_text_path(self, saved_filename: str) -> Path:
        return self.text_output_dir / f"{Path(saved_filename).stem}.txt"

    def load_saved_text(self, saved_filename: str) -> Optional[str]:
        path = self.get_text_path(saved_filename)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")


class _ImageAwareSplitter:
    _IMG_PAT = re.compile(r"--- 图片开始 ---.*?--- 图片结束 ---", re.DOTALL)

    def __init__(self) -> None:
        if not _LANGCHAIN_OK:
            raise ImportError("向量检索依赖未安装")
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.vector_chunk_size,
            chunk_overlap=settings.vector_chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def split(self, text: str) -> List[str]:
        images = list(self._IMG_PAT.finditer(text))
        if not images:
            return self._splitter.split_text(text)

        placeholder_map: Dict[str, str] = {}
        temporary = text
        for idx, match in enumerate(images):
            placeholder = f"\n<<<IMG_{idx}>>>\n"
            placeholder_map[placeholder.strip()] = match.group(0)
            temporary = temporary.replace(match.group(0), placeholder, 1)

        chunks = self._splitter.split_text(temporary)
        restored = []
        for chunk in chunks:
            for placeholder, original in placeholder_map.items():
                chunk = chunk.replace(placeholder, original)
            restored.append(chunk)
        return restored


# ---------------------------------------------------------------------------
# 向量索引与混合检索
# ---------------------------------------------------------------------------

class ChunkStore:
    """Chroma + BM25 混合检索封装。

    职责：
        - 维护本地 embedding 与 Chroma 持久化集合；
        - 提供 list_chunks / hybrid_search 等检索接口；
        - 与 DocumentProcessor 共享 gte-multilingual-base 模型目录。

    注意：
        模型目录不存在时将抛出 FileNotFoundError，需先下载或挂载权重。
    """

    def __init__(self, force_rebuild: bool = False) -> None:
        if not _LANGCHAIN_OK:
            raise ImportError("langchain/chromadb 依赖未安装")
        model_dir = Path(settings.embedding_model_dir)
        if not model_dir.exists():
            raise FileNotFoundError(f"本地向量模型不存在: {model_dir}")

        self._chroma_dir = Path(settings.chroma_db_dir)
        self._bm25_pkl = Path(settings.bm25_index_path)
        self._splitter = _ImageAwareSplitter()
        self._embeddings = HuggingFaceEmbeddings(
            model_name=str(model_dir),
            model_kwargs={"device": "cpu", "trust_remote_code": True, "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )

        if force_rebuild and self._chroma_dir.exists():
            shutil.rmtree(self._chroma_dir)
        self._chroma_dir.mkdir(parents=True, exist_ok=True)
        self._vectorstore = Chroma(
            collection_name=settings.chroma_collection_name,
            embedding_function=self._embeddings,
            persist_directory=str(self._chroma_dir),
        )
        self._all_chunks: List["Document"] = self._load_bm25_chunks()

    @property
    def available(self) -> bool:
        return True

    def upsert_text(self, text: str, meta: Optional[Dict[str, Any]] = None) -> int:
        from utils.text_cleaner import clean_parsed_text

        meta = dict(meta or {})
        text = clean_parsed_text(text)
        if "file_id" not in meta or meta.get("file_id") in (None, ""):
            standard_id = meta.get("standard_id")
            source = meta.get("source_file") or meta.get("source")
            if standard_id not in (None, ""):
                meta["file_id"] = f"standard:{standard_id}"
            elif source not in (None, ""):
                meta["file_id"] = f"source:{source}"
        chunks = [chunk for chunk in self._splitter.split(text) if chunk.strip()]
        documents = [Document(page_content=chunk, metadata=meta) for chunk in chunks]
        self.delete(meta)
        for start in range(0, len(documents), settings.vector_batch_size):
            self._vectorstore.add_documents(documents[start : start + settings.vector_batch_size])
        self._all_chunks.extend(documents)
        self._save_bm25_chunks()
        return len(documents)

    def delete(self, meta: Dict[str, Any]) -> None:
        wheres: List[Dict[str, Any]] = []
        for key in ("file_id", "standard_id", "source", "source_file"):
            value = meta.get(key)
            if value not in (None, ""):
                wheres.append({key: value})
        if not wheres:
            return
        try:
            for where in wheres:
                self._vectorstore._collection.delete(where=where)
        except Exception as exc:
            logger.warning("删除向量索引失败: %s", exc)
        self._all_chunks = [doc for doc in self._all_chunks if not self._doc_matches(doc.metadata, meta)]
        self._save_bm25_chunks()

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        semantic_ret = self._vectorstore.as_retriever(search_kwargs={"k": top_k})
        try:
            if self._all_chunks:
                bm25_ret = BM25Retriever.from_documents(self._all_chunks)
                bm25_ret.k = top_k
                retriever = EnsembleRetriever(
                    retrievers=[bm25_ret, semantic_ret],
                    weights=[settings.bm25_weight, settings.semantic_weight],
                )
            else:
                retriever = semantic_ret
            results = retriever.invoke(query)
        except Exception as exc:
            logger.warning("混合检索失败，回退语义检索: %s", exc)
            results = semantic_ret.invoke(query)
        return [{"page_content": item.page_content, "metadata": item.metadata} for item in results[:top_k]]

    def _fetch_chunks_from_vectorstore(
        self,
        where: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        try:
            payload = self._vectorstore._collection.get(
                where=where,
                include=["documents", "metadatas"],
                limit=limit,
            )
            documents = payload.get("documents") or []
            metadatas = payload.get("metadatas") or []
            for idx, content in enumerate(documents):
                if not content:
                    continue
                md = metadatas[idx] if idx < len(metadatas) else {}
                chunks.append({"page_content": content, "metadata": md or {}})
        except Exception as exc:
            logger.warning("向量库查询 chunks 失败，回退内存索引: %s", exc)
        return chunks

    def _fetch_chunks_from_bm25_cache(
        self,
        meta: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        fallback: List[Dict[str, Any]] = []
        for doc in self._all_chunks:
            if self._doc_matches(doc.metadata or {}, meta):
                fallback.append({"page_content": doc.page_content, "metadata": doc.metadata or {}})
                if len(fallback) >= limit:
                    break
        return fallback

    def list_chunks(self, meta: Dict[str, Any], limit: int = 500) -> List[Dict[str, Any]]:
        where = self._build_where(meta)
        if where:
            chunks = self._fetch_chunks_from_vectorstore(where, limit)
            if chunks:
                return chunks[:limit]
        return self._fetch_chunks_from_bm25_cache(meta, limit)

    def _build_where(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("file_id", "standard_id", "source", "source_file"):
            value = meta.get(key)
            if value not in (None, ""):
                return {key: value}
        return {}

    def _doc_matches(self, doc_meta: Dict[str, Any], target_meta: Dict[str, Any]) -> bool:
        return any(
            target_meta.get(key) not in (None, "")
            and str(doc_meta.get(key)) == str(target_meta.get(key))
            for key in ("file_id", "standard_id", "source", "source_file")
        )

    def _load_bm25_chunks(self) -> List["Document"]:
        if self._bm25_pkl.exists():
            with open(self._bm25_pkl, "rb") as file:
                return pickle.load(file)
        return []

    def _save_bm25_chunks(self) -> None:
        self._bm25_pkl.parent.mkdir(parents=True, exist_ok=True)
        with open(self._bm25_pkl, "wb") as file:
            pickle.dump(self._all_chunks, file)


_chunk_store_instance: Optional[ChunkStore] = None


def vector_store_is_available() -> bool:
    if not settings.vector_store_enabled:
        return False
    if not _LANGCHAIN_OK:
        return False
    return Path(settings.embedding_model_dir).exists()


def get_chunk_store() -> Optional[ChunkStore]:
    global _chunk_store_instance
    if not vector_store_is_available():
        return None
    if _chunk_store_instance is None:
        try:
            _chunk_store_instance = ChunkStore()
        except Exception as exc:
            logger.warning("向量检索初始化失败，将跳过该能力: %s", exc)
            return None
    return _chunk_store_instance
