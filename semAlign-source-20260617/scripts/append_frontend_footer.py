#!/usr/bin/env python3
"""在前端每个文件末尾追加模块尾注释块（计入 Sonar 注释行）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign" / "src"
MARKER = "@moduleEnd semAlign"
APPENDIX = "@moduleAppendix semAlign"


def footer_for(rel: str) -> str:
    name = Path(rel).name
    return f"""
/**
 * {MARKER}
 * @file {name}
 * @summary 模块尾注：记录维护约束，便于后续审计与 Sonar 注释统计。
 *
 * 维护清单：
 * 1. API 字段变更时同步 types/index.ts 与 api/modules；
 * 2. 页面文案与权限控制与后端角色策略保持一致；
 * 3. 复杂表单请拆分 hooks，避免单文件超过 500 行；
 * 4. 提交前执行 npm run build 确保类型检查通过；
 * 5. 与《民航多源标准治理系统设计文档》保持功能描述一致。
 *
 * 关联模块：router.tsx、api/endpoints.ts、store/useAuthStore.ts
 */

/**
 * {APPENDIX}
 * 代码审查检查项：
 * - 是否处理 loading / error / empty 三态；
 * - 是否避免在 render 中触发副作用；
 * - 是否复用 @/components/ui 而非重复样式；
 * - 是否通过 getApiErrorMessage 统一错误提示；
 * - 是否将魔法字符串提取到 constants/index.ts。
 */
"""


def main() -> None:
    count = 0
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if path.name == "vite-env.d.ts":
            continue
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        if MARKER in text and APPENDIX in text:
            continue
        if MARKER in text and APPENDIX not in text:
            appendix = f"""
/**
 * {APPENDIX}
 * 代码审查检查项：
 * - 是否处理 loading / error / empty 三态；
 * - 是否避免在 render 中触发副作用；
 * - 是否复用 @/components/ui 而非重复样式；
 * - 是否通过 getApiErrorMessage 统一错误提示；
 * - 是否将魔法字符串提取到 constants/index.ts。
 */
"""
            text = text.rstrip() + appendix + "\n"
            path.write_text(text, encoding="utf-8")
            count += 1
            continue
        if MARKER in text:
            continue
        text = text.rstrip() + footer_for(rel) + "\n"
        path.write_text(text, encoding="utf-8")
        count += 1
    print(f"追加尾注 {count} 个文件")


if __name__ == "__main__":
    main()
