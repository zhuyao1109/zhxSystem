"""
文件解析器：PDF / Excel → 标准导入行数据。

从 PDF 纯文本与 Excel 表格行抽取标准号、名称、版本等字段，
供标准导入流程校验与批量入库使用。
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

DEFAULT_STD_NAME = "未命名标准"
_PDF_PARSE_ERRORS = (OSError, IOError, AttributeError, TypeError, ValueError)
_EXCEL_PARSE_ERRORS = (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError)
_CJK_SPACE_RE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
_PREFACE_NOISE_RE = re.compile(
    r"(?:"
    r"^本标准按照|^本标准依据|给出的规则起草|"
    r"^本标准由|起草单位|主要起草人|归口|"
    r"^前\s*言$|^目\s*次$|^引\s*言$|"
    r"^发\s*布$|^实\s*施$|"
    r"^ICS\b|^CCS\b|"
    r"国家质量监督检验检疫总局|"
    r"国家市场监督管理总局|"
    r"中国?国家标准化管理委员会|"
    r"国家标准化管理委员会|"
    r"^\d{4}-\d{2}-\d{2}.*(发布|实施)"
    r")"
)
_PUBLISHER_NAME_RE = re.compile(
    r"(?:"
    r"中国?国家标准化管理委员会|"
    r"国家标准化管理委员会|"
    r"国家市场监督管理总局|"
    r"国家质量监督检验检疫总局|"
    r"中华人民共和国国家标准|"
    r"国家标准$"
    r")"
)
_SECTION_HEADING_NAMES = frozenset(
    {
        "范围",
        "规范性引用文件",
        "术语和定义",
        "术语、定义和缩略语",
        "缩略语",
        "引言",
        "前言",
        "目次",
        "参考文献",
        "附录",
    }
)
_PARTIAL_PART_TITLE_RE = re.compile(r"^第\s*\d*\s*部分")
_GENERIC_COVER_TITLES = frozenset(
    {
        "中华人民共和国国家标准",
        "中华人民共和国国家标准化指导性技术文件",
        "国家标准",
        "中华人民共和国",
        "国家标准化指导性技术文件",
    }
)


class PDFParser:
    """PDF / Excel 解析，提取标准信息"""

    def __init__(self) -> None:
        self.std_no_pattern = re.compile(
            r"([A-Z]+/[A-Z]?\s?\d+(\.\d+)*-\d{4})|"
            r"([A-Z]+\s?\d+(\.\d+)*-\d{4})|"
            r"(ISO\s?\d+:\d{4})"
        )
        self.std_no_loose_pattern = re.compile(
            r"([A-Z]+/[A-Z]?\s?\d+(\.\d+)*-\d[\d\"\"']{1,4})|"
            r"([A-Z]+\s?\d+(\.\d+)*-\d[\d\"\"']{1,4})|"
            r"(ISO\s?\d+[:：]\d{4})"
        )
        self.std_no_global_pattern = re.compile(
            r"(GB/T|MH/T|ISO)\s*[\d.\-:：／/]{3,20}"
        )
        self.main_prefixes = (
            "GB/T", "GB", "MH/T", "MH", "ISO", "IEC", "YY/T", "GA/T", "JR/T", "DB"
        )

    def _normalize_line(self, text: str) -> str:
        t = unicodedata.normalize("NFKC", text or "")
        t = (
            t.replace("／", "/")
            .replace("—", "-")
            .replace("–", "-")
            .replace("−", "-")
            .replace("：", ":")
            .replace("”", "1")
            .replace("“", "1")
        )
        # OCR 常见问题：年份中间夹空格，例如 201 1 -> 2011
        t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
        # 中文字间空格（PDF 字距）去掉，避免标题匹配失败
        t = _CJK_SPACE_RE.sub("", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _recover_year(self, candidate: str, nearby: str) -> str | None:
        """从邻近文本补全残缺年份（如 GB/T 27910-20）。"""
        m = re.search(r"([^-]+-)(\d{2,3})$", candidate)
        if not m:
            return None
        prefix = m.group(1)
        tail = m.group(2)
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", nearby)
        if years:
            return f"{prefix}{years[-1]}"
        if len(tail) == 2:
            return f"{prefix}20{tail}"
        if len(tail) == 3:
            return f"{prefix}2{tail}"
        return None

    def _normalize_standard_no(self, raw: str) -> str:
        s = self._normalize_line(raw).upper()
        s = s.replace("／", "/").replace("：", ":")
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"\s*/\s*", "/", s)
        s = re.sub(r"\s*-\s*", "-", s)
        s = re.sub(r"\s*:\s*", ":", s)
        s = s.replace("ISO/", "ISO ")
        return s

    def _is_main_standard(self, standard_no: str) -> bool:
        s = standard_no.upper()
        return any(s.startswith(prefix) for prefix in self.main_prefixes)

    def _extract_year(self, standard_no: str) -> int:
        m = re.search(r"(\d{4})$", standard_no)
        return int(m.group(1)) if m else 0

    def _base_no(self, standard_no: str) -> str:
        s = standard_no.upper().replace(" ", "")
        s = re.sub(r"[-:]\d{4}$", "", s)
        return s

    def _is_plausible_standard_no(self, standard_no: str) -> bool:
        m = re.search(r"(\d{4})$", standard_no)
        if not m:
            return True
        year = int(m.group(1))
        return 1900 <= year <= 2035

    def _is_preface_noise_line(self, line: str) -> bool:
        text = (line or "").strip()
        if not text:
            return True
        if text in _GENERIC_COVER_TITLES:
            return True
        if _PREFACE_NOISE_RE.search(text):
            return True
        if text.startswith("本标准") and len(text) <= 40:
            return True
        return False

    def _looks_like_noise_name(self, name: str) -> bool:
        if not name or name == DEFAULT_STD_NAME:
            return True
        s = name.strip()
        if re.match(r"^\[\d+\]", s):
            return True
        if len(s) < 6:
            return True
        if self._is_preface_noise_line(s):
            return True
        if _PUBLISHER_NAME_RE.search(s) and len(s) <= 20:
            return True
        if s in {"国家标准化管理委员会", "中国国家标准化管理委员会", "国家市场监督管理总局"}:
            return True
        if s in _SECTION_HEADING_NAMES or s.rstrip("：:") in _SECTION_HEADING_NAMES:
            return True
        if "给出的规则起草" in s or "本标准按照" in s or "本标准依据" in s:
            return True
        if re.search(r"[A-Z]+/?[A-Z]?\s?\d+(\.\d+)*-\d{3,4}", s):
            return True
        return False

    def _is_partial_part_title(self, name: str) -> bool:
        """仅有「第N部分…」而缺少系列名，视为不完整标题。"""
        s = (name or "").strip()
        if not s:
            return True
        if _PARTIAL_PART_TITLE_RE.match(s):
            return True
        # 「中国标准时间第部分元数据」缺数字
        if re.search(r"第\s*部分", s) and not re.search(r"第\s*\d+\s*部分", s):
            return True
        return False

    def _merge_part_number_holes(self, title: str, nearby_lines: list[str]) -> str:
        """修复『第 部分』中间缺页码数字（数字常被拆到下一行）。"""
        if not title or not re.search(r"第\s*部分", title):
            return title
        if re.search(r"第\s*\d+\s*部分", title):
            return title
        for line in nearby_lines:
            m = re.fullmatch(r"(\d{1,2})", (line or "").strip())
            if m:
                return re.sub(r"第\s*部分", f"第{m.group(1)}部分", title, count=1)
        return title

    def _pick_best_title(
        self,
        cover_title: str | None,
        candidate_title: str | None,
        file_title: str | None,
    ) -> str:
        """封面题名、候选行、文件名三者择优；文件名在本语料里通常最完整。"""
        def usable(t: str | None) -> bool:
            return bool(t) and not self._looks_like_noise_name(t) and not self._is_partial_part_title(t)

        # 有可靠文件名时优先：封面/候选经常抽到「规范性引用文件」等章节名
        if usable(file_title):
            if not usable(cover_title) and not usable(candidate_title):
                return file_title  # type: ignore[return-value]
            for other in (cover_title, candidate_title):
                if not usable(other):
                    continue
                assert other is not None and file_title is not None
                if other in file_title or file_title.endswith(other):
                    return file_title
                if len(file_title) >= len(other):
                    return file_title
            return file_title  # type: ignore[return-value]

        for t in (cover_title, candidate_title):
            if usable(t):
                return t  # type: ignore[return-value]
        return (file_title or candidate_title or cover_title or DEFAULT_STD_NAME)[:120]

    def _title_from_source_name(self, source_name: str | None) -> str | None:
        """用上传文件名推断标题（去掉时间戳前缀与扩展名）。"""
        if not source_name:
            return None
        stem = Path(source_name).stem
        stem = re.sub(r"^\d{8}_\d{6}_", "", stem).strip()
        stem = _CJK_SPACE_RE.sub("", stem)
        stem = re.sub(r"\s+", " ", stem).strip(" ._-")
        if len(stem) < 6:
            return None
        if self._is_preface_noise_line(stem):
            return None
        if "给出的规则起草" in stem or stem.startswith("本标准按照"):
            return None
        cjk = len(re.findall(r"[\u4e00-\u9fff]", stem))
        if cjk < 4 and len(stem) < 8:
            return None
        return stem[:120]

    def _is_title_candidate_line(self, line: str) -> bool:
        if not line or self._is_preface_noise_line(line):
            return False
        if self.std_no_pattern.search(line) or self.std_no_loose_pattern.search(line):
            return False
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", line))
        return cjk_count >= 4 and len(line) >= 6

    def _classify_title_line(self, short: str) -> str | None:
        if short in _GENERIC_COVER_TITLES or self._is_preface_noise_line(short):
            return None
        if short.startswith("本标准"):
            return None
        if any(
            k in short
            for k in ("指南", "规范", "要求", "方法", "数据", "流程", "接口", "字典", "协议")
        ):
            return "preferred"
        if "标准" in short and not short.startswith("本"):
            return "preferred"
        return "fallback"

    def _collect_title_candidates(
        self, normalized_lines: List[str]
    ) -> tuple[List[str], List[str]]:
        preferred: List[str] = []
        fallback: List[str] = []
        for line in normalized_lines[:120]:
            if not self._is_title_candidate_line(line):
                continue
            short = line[:100]
            category = self._classify_title_line(short)
            if category == "preferred":
                preferred.append(short)
            elif category == "fallback":
                fallback.append(short)
        return preferred, fallback

    def _infer_cover_title(
        self, normalized_lines: List[str]
    ) -> tuple[str | None, str | None]:
        """从封面标准号后的中文行拼接真正标准名称。"""
        cover = normalized_lines[:60]
        std_idx = None
        main_std = None
        for idx, line in enumerate(cover):
            if not line or re.search(r"(按照|依据|引用|代替)", line):
                continue
            match = self.std_no_pattern.search(line) or self.std_no_loose_pattern.search(line)
            if not match:
                continue
            cand = self._normalize_standard_no(match.group(0))
            if not self._is_main_standard(cand) or not self._is_plausible_standard_no(cand):
                continue
            remaining = line.replace(match.group(0), "", 1).strip()
            if len(remaining) > 20 and not self._looks_like_noise_name(remaining):
                return cand, remaining[:120]
            std_idx = idx
            main_std = cand
            break
        if std_idx is None or main_std is None:
            return None, None

        parts: List[str] = []
        nearby_for_digits: List[str] = []
        for line in cover[std_idx + 1 : std_idx + 10]:
            if not line:
                if parts:
                    break
                continue
            nearby_for_digits.append(line)
            if self.std_no_pattern.search(line) or self.std_no_loose_pattern.search(line):
                break
            if re.search(r"\d{4}-\d{2}-\d{2}", line) and ("发布" in line or "实施" in line):
                break
            if self._is_preface_noise_line(line):
                break
            if re.match(r"^(代替|部分代替)", line):
                continue
            # 单独数字行：可能是「第2部分」被拆开的页码/部分号
            if re.fullmatch(r"\d{1,2}", line.strip()):
                if parts and re.search(r"第\s*$", parts[-1]):
                    parts[-1] = parts[-1].rstrip() + line.strip()
                elif parts and "第" in "".join(parts) and "部分" in "".join(parts):
                    # 已有「第 部分」占位，稍后统一填数字
                    pass
                continue
            if line.strip() in {":", "：", "-", "—"}:
                continue
            cjk = len(re.findall(r"[\u4e00-\u9fff]", line))
            latin = len(re.findall(r"[A-Za-z]", line))
            if latin >= 8 and cjk < 2:
                break
            if cjk >= 2:
                parts.append(line[:80])
            if sum(len(p) for p in parts) >= 60:
                break
        if not parts:
            return main_std, None
        title = "".join(parts)
        title = _CJK_SPACE_RE.sub("", title)
        title = re.sub(r"\s+", " ", title).strip()
        title = self._merge_part_number_holes(title, nearby_for_digits)
        if self._looks_like_noise_name(title) or self._is_partial_part_title(title):
            # 仍不完整则交由上层与文件名择优
            return main_std, title[:120] if title else None
        return main_std, title[:120] if title else None

    def _infer_doc_title(
        self, normalized_lines: List[str], source_name: str | None = None
    ) -> str:
        """推断文档标题：封面 / 候选行 / 文件名择优。"""
        _, cover_title = self._infer_cover_title(normalized_lines)
        preferred, fallback = self._collect_title_candidates(normalized_lines)
        candidate_title = None
        for cand in preferred + fallback:
            if not self._looks_like_noise_name(cand) and not self._is_partial_part_title(cand):
                candidate_title = cand
                break
        file_title = self._title_from_source_name(source_name)
        return self._pick_best_title(cover_title, candidate_title, file_title)

    def _extract_standard_no_from_line(
        self, line: str, idx: int, normalized_lines: List[str]
    ) -> str | None:
        match = self.std_no_pattern.search(line)
        if match:
            return match.group(0).strip()
        loose = self.std_no_loose_pattern.search(line)
        if not loose:
            return None
        cand = loose.group(0).strip()
        cand = re.sub(r"[-:：](\d{1,3})$", r"-\1", cand)
        nearby = " ".join(normalized_lines[idx : idx + 8])
        recovered = self._recover_year(cand, nearby)
        return recovered or cand

    def _build_record_from_line(
        self, line: str, standard_no: str, doc_title: str
    ) -> Dict[str, Any] | None:
        standard_no = self._normalize_standard_no(standard_no)
        if not self._is_plausible_standard_no(standard_no):
            return None
        # 前言里“按照 GB/T1.1—2009 给出的规则起草”不应生成主记录名称污染
        if re.search(r"(按照|依据|引用)", line) and standard_no.replace(" ", "").startswith(
            ("GB/T1.1", "GB/T1.0", "GB1.1")
        ):
            return None
        remaining = line.replace(standard_no, "", 1).strip()
        # 宽松匹配时 line 里可能还是弯引号年份写法，再清一次
        remaining = self.std_no_pattern.sub("", remaining).strip()
        remaining = self.std_no_loose_pattern.sub("", remaining).strip()
        version_pattern = r"(V?\d+\.\d+|\d+\.\d+\.\d+)"
        version_match = re.search(version_pattern, remaining)
        if version_match:
            version = version_match.group(0)
            name = remaining.replace(version, "", 1).strip()
        else:
            name = remaining
            version = "未知"
        if self._looks_like_noise_name(name):
            name = doc_title
        return {
            "standard_no": standard_no,
            "name": name if name else DEFAULT_STD_NAME,
            "version": version,
        }

    def _extract_records_from_lines(
        self, normalized_lines: List[str], doc_title: str
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for idx, line in enumerate(normalized_lines):
            if not line:
                continue
            standard_no = self._extract_standard_no_from_line(line, idx, normalized_lines)
            if not standard_no:
                continue
            record = self._build_record_from_line(line, standard_no, doc_title)
            if record:
                records.append(record)
        return records

    def _fallback_global_records(self, text: str, doc_title: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        normalized_full_text = self._normalize_line(text)
        for m in self.std_no_global_pattern.finditer(normalized_full_text):
            candidate = self._normalize_standard_no(m.group(0))
            strict_match = self.std_no_pattern.search(candidate)
            if not strict_match:
                continue
            standard_no = self._normalize_standard_no(strict_match.group(0))
            if not self._is_plausible_standard_no(standard_no):
                continue
            records.append(
                {
                    "standard_no": standard_no,
                    "name": doc_title,
                    "version": "未知",
                }
            )
        return records

    def _filter_to_main_standards(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        main_records = [r for r in records if self._is_main_standard(r["standard_no"])]
        return main_records or records

    def _prefer_cover_standard(
        self, records: List[Dict[str, Any]], cover_std: str | None, doc_title: str
    ) -> List[Dict[str, Any]]:
        """若识别到封面主标准号，优先把它放在第一条并修正名称。"""
        if not records:
            return records
        if cover_std:
            cover_key = self._normalize_standard_no(cover_std)
            for item in records:
                if self._normalize_standard_no(item["standard_no"]) == cover_key:
                    if self._looks_like_noise_name(item.get("name", "")):
                        item["name"] = doc_title
                    # 封面主标准置顶
                    others = [
                        r
                        for r in records
                        if self._normalize_standard_no(r["standard_no"]) != cover_key
                    ]
                    return [item] + others
        # 没有封面号时，至少修正脏名称
        for item in records:
            if self._looks_like_noise_name(item.get("name", "")):
                item["name"] = doc_title
        return records

    def _deduplicate_by_standard_no(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        dedup: dict[str, Dict[str, Any]] = {}
        for item in records:
            key = item["standard_no"]
            if key not in dedup:
                dedup[key] = item
                continue
            old_name = dedup[key].get("name", "")
            new_name = item.get("name", "")
            if self._looks_like_noise_name(old_name) and not self._looks_like_noise_name(new_name):
                dedup[key] = item
        return list(dedup.values())

    def _keep_latest_versions(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        latest: dict[str, Dict[str, Any]] = {}
        for item in records:
            base = self._base_no(item["standard_no"])
            if base not in latest:
                latest[base] = item
                continue
            old = latest[base]
            if self._extract_year(item["standard_no"]) > self._extract_year(old["standard_no"]):
                latest[base] = item
        return list(latest.values())

    def parse_text(
        self, text: str, source_name: str | None = None
    ) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            raise ValueError("文本内容为空，无法提取标准信息")

        normalized_lines = [self._normalize_line(x) for x in text.split("\n")]
        cover_std, _ = self._infer_cover_title(normalized_lines)
        doc_title = self._infer_doc_title(normalized_lines, source_name=source_name)

        records = self._extract_records_from_lines(normalized_lines, doc_title)
        if not records:
            records = self._fallback_global_records(text, doc_title)

        records = self._filter_to_main_standards(records)
        records = self._deduplicate_by_standard_no(records)
        records = self._keep_latest_versions(records)
        records = self._prefer_cover_standard(records, cover_std, doc_title)

        if not records:
            raise ValueError(
                "未能从文本中提取到任何标准信息，请确保文档包含标准编号"
            )
        return records

    async def parse_pdf(
        self, file_content: bytes, source_name: str | None = None
    ) -> List[Dict[str, Any]]:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                if not full_text.strip():
                    raise ValueError("PDF 文件中没有可提取的文本内容")
                return self.parse_text(full_text, source_name=source_name)
        except ValueError:
            raise
        except _PDF_PARSE_ERRORS as e:
            logger.error("PDF 解析失败: %s", e, exc_info=True)
            raise RuntimeError(f"PDF 解析失败: {e}") from e

    def _require_excel_columns(self, df: pd.DataFrame) -> None:
        required_columns = ["standard_no", "name", "version"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Excel 文件缺少必需的列: {col}")

    def _excel_optional_field(self, row: pd.Series, column: str, default: str) -> str:
        if column in row and pd.notna(row.get(column)):
            return str(row.get(column, default)).strip()
        return default

    def _excel_row_to_record(self, row: pd.Series) -> Dict[str, Any]:
        return {
            "standard_no": str(row["standard_no"]).strip(),
            "name": str(row["name"]).strip(),
            "version": str(row["version"]).strip(),
            "status": self._excel_optional_field(row, "status", "有效"),
            "category": self._excel_optional_field(row, "category", "未分类"),
            "department": self._excel_optional_field(row, "department", ""),
            "description": self._excel_optional_field(row, "description", ""),
        }

    def _parse_excel_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        self._require_excel_columns(df)
        records = [self._excel_row_to_record(row) for _, row in df.iterrows()]
        if not records:
            raise ValueError("Excel 文件中没有有效数据")
        return records

    async def parse_excel(self, file_content: bytes) -> List[Dict[str, Any]]:
        try:
            df = pd.read_excel(io.BytesIO(file_content))
            return self._parse_excel_dataframe(df)
        except ValueError:
            raise
        except _EXCEL_PARSE_ERRORS as e:
            logger.error("Excel 解析失败: %s", e, exc_info=True)
            raise RuntimeError(f"Excel 解析失败: {e}") from e

    async def parse(
        self, file_content: bytes, file_type: str, source_name: str | None = None
    ) -> List[Dict[str, Any]]:
        """统一入口：file_type 为 pdf 或 excel"""
        if file_type == "pdf":
            return await self.parse_pdf(file_content, source_name=source_name)
        if file_type in ("excel", "xlsx", "xls"):
            return await self.parse_excel(file_content)
        raise ValueError(f"不支持的文件类型: {file_type}")


pdf_parser = PDFParser()
