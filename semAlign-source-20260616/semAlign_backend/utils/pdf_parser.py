"""
文件解析器：PDF / Excel → 标准导入行数据。

从 PDF 纯文本与 Excel 表格行抽取标准号、名称、版本等字段，
供标准导入流程校验与批量入库使用。
"""

import io
import logging
import re
import unicodedata
from typing import Any, Dict, List

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

DEFAULT_STD_NAME = "未命名标准"
_PDF_PARSE_ERRORS = (OSError, IOError, AttributeError, TypeError, ValueError)
_EXCEL_PARSE_ERRORS = (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError)


class PDFParser:
    """PDF / Excel 解析，提取标准信息"""

    def __init__(self) -> None:
        """函数内部辅助：init  。"""
        self.std_no_pattern = re.compile(
            r"([A-Z]+/[A-Z]?\s?\d+(\.\d+)*-\d{4})|"
            r"([A-Z]+\s?\d+(\.\d+)*-\d{4})|"
            r"(ISO\s?\d+:\d{4})"
        )
        self.std_no_loose_pattern = re.compile(
            r"([A-Z]+/[A-Z]?\s?\d+(\.\d+)*-\d[\d”\"]{1,4})|"
            r"([A-Z]+\s?\d+(\.\d+)*-\d[\d”\"]{1,4})|"
            r"(ISO\s?\d+[:：]\d{4})"
        )
        self.std_no_global_pattern = re.compile(
            r"(GB/T|MH/T|ISO)\s*[\d.\-:：／/]{3,20}"
        )
        # 主标准体系前缀（用于过滤参考文献/引用标准噪声，如 ANSI X9.*）
        self.main_prefixes = (
            "GB/T", "GB", "MH/T", "MH", "ISO", "IEC", "YY/T", "GA/T", "JR/T", "DB"
        )

    def _normalize_line(self, text: str) -> str:
        """函数内部辅助：normalize line。"""
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
        # 压缩多余空格
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _recover_year(self, candidate: str, nearby: str) -> str | None:
        # candidate 如 GB/T 27910-20 或 GB/T 27910-201
        """函数内部辅助：recover year。"""
        m = re.search(r"([^-]+-)(\d{2,3})$", candidate)
        if not m:
            return None
        prefix = m.group(1)
        tail = m.group(2)
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", nearby)
        if years:
            return f"{prefix}{years[-1]}"
        if len(tail) == 2:
            # 20 -> 2010/2020 这种无法确定，优先按 20xx 猜测
            return f"{prefix}20{tail}"
        if len(tail) == 3:
            return f"{prefix}2{tail}"
        return None

    def _normalize_standard_no(self, raw: str) -> str:
        """函数内部辅助：normalize standard no。"""
        s = self._normalize_line(raw).upper()
        s = s.replace("／", "/").replace("：", ":")
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"\s*/\s*", "/", s)
        s = re.sub(r"\s*-\s*", "-", s)
        s = re.sub(r"\s*:\s*", ":", s)
        s = s.replace("ISO/", "ISO ")
        return s

    def _is_main_standard(self, standard_no: str) -> bool:
        """函数内部辅助：is main standard。"""
        s = standard_no.upper()
        return any(s.startswith(prefix) for prefix in self.main_prefixes)

    def _extract_year(self, standard_no: str) -> int:
        """函数内部辅助：extract year。"""
        m = re.search(r"(\d{4})$", standard_no)
        return int(m.group(1)) if m else 0

    def _base_no(self, standard_no: str) -> str:
        # GB/T 27910-2012 -> GB/T27910；ISO 9001:2015 -> ISO9001
        """函数内部辅助：base no。"""
        s = standard_no.upper().replace(" ", "")
        s = re.sub(r"[-:]\d{4}$", "", s)
        return s

    def _looks_like_noise_name(self, name: str) -> bool:
        """函数内部辅助：looks like noise name。"""
        if not name or name == DEFAULT_STD_NAME:
            return True
        s = name.strip()
        # 引用编号行、残缺短语、标准号残留等都视为脏名称
        if re.match(r"^\[\d+\]", s):
            return True
        if len(s) < 6:
            return True
        if re.search(r"[A-Z]+/?[A-Z]?\s?\d+(\.\d+)*-\d{3,4}", s):
            return True
        return False

    def _is_title_candidate_line(self, line: str) -> bool:
        """函数内部辅助：is title candidate line。"""
        if not line:
            return False
        if self.std_no_pattern.search(line) or self.std_no_loose_pattern.search(line):
            return False
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", line))
        return cjk_count >= 4 and len(line) >= 6

    def _classify_title_line(self, short: str, generic_titles: set[str]) -> str | None:
        """函数内部辅助：classify title line。"""
        if short in generic_titles:
            return None
        if any(k in short for k in ("金融", "信息安全", "指南", "规范", "要求", "标准")):
            return "preferred"
        return "fallback"

    def _collect_title_candidates(
        self, normalized_lines: List[str]
    ) -> tuple[List[str], List[str]]:
        """函数内部辅助：collect title candidates。"""
        generic_titles = {
            "中华人民共和国国家标准",
            "国家标准",
            "中华人民共和国",
        }
        preferred: List[str] = []
        fallback: List[str] = []
        for line in normalized_lines[:120]:
            if not self._is_title_candidate_line(line):
                continue
            short = line[:100]
            category = self._classify_title_line(short, generic_titles)
            if category == "preferred":
                preferred.append(short)
            elif category == "fallback":
                fallback.append(short)
        return preferred, fallback

    def _infer_doc_title(self, normalized_lines: List[str]) -> str:
        """函数内部辅助：infer doc title。"""
        preferred, fallback = self._collect_title_candidates(normalized_lines)
        if preferred:
            return preferred[0]
        if fallback:
            return fallback[0]
        return DEFAULT_STD_NAME

    def _is_plausible_standard_no(self, standard_no: str) -> bool:
        """函数内部辅助：is plausible standard no。"""
        m = re.search(r"(\d{4})$", standard_no)
        if not m:
            return True
        year = int(m.group(1))
        return 1900 <= year <= 2035

    async def parse_pdf(self, file_content: bytes) -> List[Dict[str, Any]]:
        """函数：parse pdf。"""
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                if not full_text.strip():
                    raise ValueError("PDF 文件中没有可提取的文本内容")
                return self.parse_text(full_text)
        except ValueError:
            raise
        except _PDF_PARSE_ERRORS as e:
            logger.error("PDF 解析失败: %s", e, exc_info=True)
            raise RuntimeError(f"PDF 解析失败: {e}") from e

    def _extract_standard_no_from_line(
        self, line: str, idx: int, normalized_lines: List[str]
    ) -> str | None:
        """函数内部辅助：extract standard no from line。"""
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
        """函数内部辅助：build record from line。"""
        standard_no = self._normalize_standard_no(standard_no)
        if not self._is_plausible_standard_no(standard_no):
            return None
        remaining = line.replace(standard_no, "", 1).strip()
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
        """函数内部辅助：extract records from lines。"""
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
        """函数内部辅助：fallback global records。"""
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
        """函数内部辅助：filter to main standards。"""
        main_records = [r for r in records if self._is_main_standard(r["standard_no"])]
        if main_records:
            return main_records
        return records

    def _deduplicate_by_standard_no(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """函数内部辅助：deduplicate by standard no。"""
        dedup: dict[str, Dict[str, Any]] = {}
        for item in records:
            key = item["standard_no"]
            if key not in dedup:
                dedup[key] = item
                continue
            if dedup[key].get("name") in ("", DEFAULT_STD_NAME) and item.get("name") not in (
                "",
                DEFAULT_STD_NAME,
            ):
                dedup[key] = item
        return list(dedup.values())

    def _keep_latest_versions(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """函数内部辅助：keep latest versions。"""
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

    def parse_text(self, text: str) -> List[Dict[str, Any]]:
        """函数：parse text。"""
        if not text or not text.strip():
            raise ValueError("文本内容为空，无法提取标准信息")

        normalized_lines = [self._normalize_line(x) for x in text.split("\n")]
        doc_title = self._infer_doc_title(normalized_lines)

        records = self._extract_records_from_lines(normalized_lines, doc_title)
        if not records:
            records = self._fallback_global_records(text, doc_title)

        records = self._filter_to_main_standards(records)
        records = self._deduplicate_by_standard_no(records)
        records = self._keep_latest_versions(records)

        if not records:
            raise ValueError(
                "未能从文本中提取到任何标准信息，请确保文档包含标准编号"
            )
        return records

    def _require_excel_columns(self, df: pd.DataFrame) -> None:
        """函数内部辅助：require excel columns。"""
        required_columns = ["standard_no", "name", "version"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Excel 文件缺少必需的列: {col}")

    def _excel_optional_field(self, row: pd.Series, column: str, default: str) -> str:
        """函数内部辅助：excel optional field。"""
        if column in row and pd.notna(row.get(column)):
            return str(row.get(column, default)).strip()
        return default

    def _excel_row_to_record(self, row: pd.Series) -> Dict[str, Any]:
        """函数内部辅助：excel row to record。"""
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
        """函数内部辅助：parse excel dataframe。"""
        self._require_excel_columns(df)
        records = [self._excel_row_to_record(row) for _, row in df.iterrows()]
        if not records:
            raise ValueError("Excel 文件中没有有效数据")
        return records

    async def parse_excel(self, file_content: bytes) -> List[Dict[str, Any]]:
        """函数：parse excel。"""
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
        _ = source_name
        if file_type == "pdf":
            return await self.parse_pdf(file_content)
        if file_type in ("excel", "xlsx", "xls"):
            return await self.parse_excel(file_content)
        raise ValueError(f"不支持的文件类型: {file_type}")


pdf_parser = PDFParser()
