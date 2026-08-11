#!/usr/bin/env python3
"""扩展前端文件头为更长的多行说明。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign" / "src"
MARKER = "@file semAlign"


EXTRA = """
 * 架构位置：SemAlign Web SPA（React 19 + Vite 6）
 * 数据流：页面组件 → service/hooks → api/modules → FastAPI
 * 权限：普通用户只读已发布对齐结果；管理员可导入与审核
 * 测试：关键路径需与后端契约测试（comparison / alignment API）联动验证
"""


def main() -> None:
    n = 0
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx"} or path.name == "vite-env.d.ts":
            continue
        text = path.read_text(encoding="utf-8")
        if "架构位置：SemAlign Web SPA" in text:
            continue
        if MARKER not in text:
            continue
        text = text.replace(
            " * - 与后端契约以 semAlign_backend OpenAPI 为准。\n */",
            " * - 与后端契约以 semAlign_backend OpenAPI 为准。\n" + EXTRA + " */",
            1,
        )
        path.write_text(text, encoding="utf-8")
        n += 1
    print(f"扩展文件头 {n} 个")


if __name__ == "__main__":
    main()
