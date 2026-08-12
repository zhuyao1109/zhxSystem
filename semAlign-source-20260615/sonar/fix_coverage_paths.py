#!/usr/bin/env python3
"""将 coverage.xml 中的文件路径加上 semAlign_backend/ 前缀，供 Sonar 单仓多模块扫描解析。"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PREFIX = "semAlign_backend/"
REPO_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_FILE = REPO_ROOT / "semAlign_backend" / "coverage.xml"


def main() -> int:
    if not COVERAGE_FILE.is_file():
        print(f"错误: 未找到 {COVERAGE_FILE}", file=sys.stderr)
        return 1

    tree = ET.parse(COVERAGE_FILE)
    root = tree.getroot()

    sources = root.find("sources")
    if sources is not None:
        sources.clear()
        ET.SubElement(sources, "source").text = "semAlign_backend"

    for cls in root.iter("class"):
        filename = cls.get("filename")
        if filename and filename.startswith(PREFIX):
            cls.set("filename", filename[len(PREFIX) :])

    tree.write(COVERAGE_FILE, encoding="unicode", xml_declaration=True)
    print(f"已修正覆盖率路径: {COVERAGE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
