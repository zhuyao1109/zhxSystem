import re
from datetime import datetime
from typing import Dict, Any, Optional

DATE_FMT_YMD = "%Y-%m-%d"

class MetadataExtractor:
    def extract(self, file_path: str, original_name: str = "") -> Dict[str, Any]:
        """从文件名和内容中提取元数据"""
        metadata = {
            "document_name": original_name or file_path.split('/')[-1],
            "publisher": "",
            "publish_date": None,
            "version": "v1.0",
            "standard_type": "recommended",
            "applicable_scope": "domestic",
            "language": "zh"
        }
        
        # 从文件名中提取信息
        self._extract_from_filename(metadata, original_name or file_path)
        
        return metadata
    
    def _extract_publisher(self, filename_lower: str) -> str:
        org_patterns = {
            "中航信": ["中航信", "cata"],
            "IATA": ["iata", "国际航空运输协会"],
            "ICAO": ["icao", "国际民航组织"],
            "中国民航局": ["民航局", "caac"]
        }
        for org, patterns in org_patterns.items():
            if any(pattern in filename_lower for pattern in patterns):
                return org
        return "未知机构"

    def _parse_date_match(self, match: re.Match) -> datetime:
        if len(match.groups()) == 3:
            date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        elif len(match.groups()) == 2:
            date_str = f"{match.group(1)}-{match.group(2)}-01"
        else:
            date_str = f"{match.group(1)}-01-01"
        return datetime.strptime(date_str, DATE_FMT_YMD)

    def _extract_publish_date(self, filename: str) -> Optional[datetime]:
        date_patterns = [
            r'(\d{4})[-_](\d{2})[-_](\d{2})',
            r'(\d{4})[-_](\d{2})',
            r'(\d{4})年'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if not match:
                continue
            try:
                return self._parse_date_match(match)
            except (ValueError, TypeError):
                continue
        return None

    def _classify_standard(self, filename_lower: str, metadata: Dict[str, Any]) -> None:
        if any(keyword in filename_lower for keyword in ["国际", "iata", "icao", "iso"]):
            metadata["applicable_scope"] = "international"
        if any(keyword in filename_lower for keyword in ["强制", "必须", "mandatory"]):
            metadata["standard_type"] = "mandatory"
        elif any(keyword in filename_lower for keyword in ["技术", "technical"]):
            metadata["standard_type"] = "technical"

    def _extract_from_filename(self, metadata: Dict[str, Any], filename: str):
        """从文件名中提取元数据"""
        filename_lower = filename.lower()
        metadata["publisher"] = self._extract_publisher(filename_lower)
        version_match = re.search(r'v(\d+\.\d+)', filename_lower)
        if version_match:
            metadata["version"] = f"v{version_match.group(1)}"
        publish_date = self._extract_publish_date(filename)
        if publish_date:
            metadata["publish_date"] = publish_date
        self._classify_standard(filename_lower, metadata)