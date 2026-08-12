import os
# --- 关键补丁：防止 Windows OpenMP 冲突 & 禁用 MKLDNN ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
# ----------------------------------------------------

import re
import json
import fitz  # PyMuPDF
import numpy as np
import argparse
import warnings
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# 尝试导入 PaddleOCR
try:
    from paddleocr import PaddleOCR
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("⚠️ 警告: 未检测到 paddleocr 库。")

warnings.filterwarnings('ignore', category=Warning)

@dataclass
class ExtractedText:
    page: int
    text: str
    bbox: Tuple[float, float, float, float]
    source: str = "text_layer"

class PDFTextExtractor:
    def __init__(self, use_ocr_fallback: bool = True):
        self.use_ocr_fallback = use_ocr_fallback and HAS_OCR
        self.ocr_engine = None
        
        if self.use_ocr_fallback:
            print("🚀 初始化 OCR 引擎 (PaddleOCR v2.7)...")
            # v2.7 接口初始化
            self.ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        
        # 即使 OCR 了，保留这个映射表来修复 OCR 可能识别错的形近字
        self.gb_standard_mapping = {
            '犌犅/犜３９４４５-２０２０': 'GB/T 39445-2020',
        }

    def _standardize_format(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.replace(' .', '.').replace(' ,', ',').replace(' :', ':').replace(' ;', ';')
        return text.strip()

    def extract_structured_clauses(self, pdf_path: str) -> Dict:
        print(f"📄 处理文件: {os.path.basename(pdf_path)}")
        extracted_texts = self._smart_extract_text(pdf_path)
        
        if not extracted_texts:
            print("❌ 无法提取任何文本")
            return {}
        
        print(f"✅ 提取完成: {len(extracted_texts)} 页")
        full_text = "\n".join([et.text for et in extracted_texts])
        
        structured_data = {
            "metadata": {
                "filename": os.path.basename(pdf_path),
                "total_pages": len(extracted_texts),
            },
            "full_text": full_text,
            "pages": [asdict(et) for et in extracted_texts],
        }
        return structured_data

    _GARBLED_MARKERS = ['犌', '犅', '犜', '犐', '犆', '犛', '犃', '犇', '']

    def _needs_ocr(self, raw_text: str, page_idx: int) -> bool:
        if not raw_text:
            return True
        if any(marker in raw_text for marker in self._GARBLED_MARKERS):
            print(f"   ⚠️ 第 {page_idx} 页检测到编码崩坏 (GB乱码)，强制切换 OCR 模式...")
            return True
        return False

    def _resolve_page_text(self, page, raw_text: str, page_idx: int) -> Tuple[str, str]:
        if not self._needs_ocr(raw_text, page_idx):
            return raw_text, "text_layer"
        if not self.use_ocr_fallback:
            return raw_text, "text_layer"
        ocr_text = self._perform_ocr(page)
        if ocr_text and len(ocr_text) > 10:
            return ocr_text, "ocr"
        return raw_text, "text_layer"

    def _extract_page_text(self, page, page_idx: int) -> Optional[ExtractedText]:
        raw_text = page.get_text("text").strip()
        final_text, source = self._resolve_page_text(page, raw_text, page_idx)
        final_text = self._standardize_format(final_text)
        if not final_text:
            print(f"⚠️ 第 {page_idx} 页无有效内容")
            return None
        return ExtractedText(page=page_idx, text=final_text, bbox=page.rect, source=source)

    def _smart_extract_text(self, pdf_path: str) -> List[ExtractedText]:
        extracted_texts = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_idx = page_num + 1
                extracted = self._extract_page_text(page, page_idx)
                if extracted:
                    extracted_texts.append(extracted)
            doc.close()
        except Exception as e:
            print(f"❌ 提取流程出错: {e}")
            import traceback
            traceback.print_exc()
        return extracted_texts

    def _perform_ocr(self, page) -> str:
        if not self.ocr_engine: return ""
        try:
            # 提高分辨率 zoom=2.0，对小字识别很有帮助
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            if pix.alpha: pix = fitz.Pixmap(fitz.csRGB, pix)
            
            # 必须 copy() 保证内存连续
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n).copy()
            
            # v2.7 接口调用
            result = self.ocr_engine.ocr(img_data, cls=True)
            
            if not result or not result[0]: return ""
            
            lines = [line[1][0] for line in result[0]]
            return "\n".join(lines)
            
        except Exception as e:
            print(f"⚠️ OCR 识别出错: {e}")
            return ""

    def save_results(self, data: Dict, output_dir: str, filename: str):
        os.makedirs(output_dir, exist_ok=True)
        text_path = os.path.join(output_dir, f"{filename}_text.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(data.get("full_text", ""))
        print(f"💾 结果已保存至: {output_dir}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"❌ 文件不存在: {args.pdf_path}")
        return
        
    print("=" * 60)
    print("🔍 Pro PDF Extractor (Auto-Fix GB Garbled)")
    print("=" * 60)
    
    extractor = PDFTextExtractor(use_ocr_fallback=True)
    data = extractor.extract_structured_clauses(args.pdf_path)
    
    if data:
        base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        extractor.save_results(data, args.output, base_name)
        print("\n✨ 处理完成!")

if __name__ == "__main__":
    main()
