#!/usr/bin/env python3
"""为 types/index.ts 与 constants/index.ts 补充多行 JSDoc。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign" / "src"


def _multiline_jsdoc(indent: str, name: str, kind: str, note: str) -> str:
    return (
        f"{indent}/**\n"
        f"{indent} * {kind} `{name}`：{note}\n"
        f"{indent} * @remarks 与后端 schemas 保持一致，变更需双向同步。\n"
        f"{indent} * @packageDocumentation 全局类型与常量定义\n"
        f"{indent} */\n"
    )


def enrich_exports(path: Path, kind_label: str, default_note: str) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    added = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)export\s+(interface|type|const)\s+(\w+)", line)
        if m:
            indent, kind, name = m.group(1), m.group(2), m.group(3)
            # 跳过已有完整 JSDoc
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            prev = lines[j].strip() if j >= 0 else ""
            if prev.startswith("/**") and "@remarks" in "".join(lines[max(0, j - 1) : i + 1]):
                out.append(line)
                i += 1
                continue
            # 去掉紧邻的单行 // 注释，换成 JSDoc
            if prev.startswith("//"):
                while out and out[-1].strip().startswith("//"):
                    out.pop()
            note = default_note
            if j >= 0 and lines[j].strip().startswith("//"):
                note = lines[j].strip().lstrip("/ ").strip()
            out.append(_multiline_jsdoc(indent, name, kind_label, note))
            added += 1
        out.append(line)
        i += 1
    path.write_text("".join(out), encoding="utf-8")
    return added


def main() -> None:
    n1 = enrich_exports(ROOT / "types" / "index.ts", "接口", "描述业务数据结构")
    n2 = enrich_exports(ROOT / "constants" / "index.ts", "常量", "描述前端业务常量配置")
    print(f"types: {n1}, constants: {n2}")


if __name__ == "__main__":
    main()
