#!/usr/bin/env python3
"""修复 enrich 脚本误插入的 docstring 位置。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign_backend"


def fix_abstractmethod_docstring(text: str) -> str:
    return re.sub(
        r"(@abstractmethod)\n\s+\"\"\"[^\"]+\"\"\"\n(\s+def )",
        r"\1\n\2",
        text,
    )


def fix_dataclass_field_docstring(text: str) -> str:
    # source: str = ""\n        """..."""\n    def
    return re.sub(
        r"(source: str = \"\")\n\s+\"\"\"[^\"]+\"\"\"\n(\s+def )",
        r"\1\n\2",
        text,
    )


def add_class_docstrings_priority_rules(text: str) -> str:
    if 'class BaseRule(ABC):\n    @abstractmethod' in text and 'class BaseRule(ABC):\n    """' not in text:
        text = text.replace(
            "class BaseRule(ABC):\n    @abstractmethod",
            'class BaseRule(ABC):\n    """优先级规则抽象基类，定义条款对与元数据评估接口。"""\n\n    @abstractmethod',
        )
    return text


def main() -> None:
    for path in ROOT.rglob("*.py"):
        if ".venv" in str(path) or path.parts[-2:] == ("tests",):
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        text = fix_abstractmethod_docstring(text)
        text = fix_dataclass_field_docstring(text)
        if path.name == "priority_rules.py":
            text = add_class_docstrings_priority_rules(text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            print("fixed", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
