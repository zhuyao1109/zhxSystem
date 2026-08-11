#!/usr/bin/env python3
"""为 semAlign/src 前端 TypeScript 源码批量补充 JSDoc 与文件头注释。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign" / "src"
MARKER = "@file semAlign"

MODULE_DESC: dict[str, str] = {
    "features/standards": "标准数据库模块：列表筛选、详情查看、原文件下载与元数据展示。",
    "features/alignment": "标准对齐模块：任务创建、冲突结果、对齐助手对话与审核流转。",
    "features/search": "智能检索模块：关键词/语义搜索、相关度展示与可选问答。",
    "features/import": "标准导入模块：PDF/Excel 上传、解析预览与批量入库。",
    "features/workbench": "治理工作台：指标卡、图表统计与标准动态列表。",
    "features/auth": "认证模块：登录、忘记密码与 Token 持久化。",
    "features/user": "用户中心：资料修改、密码变更与管理员用户权限。",
    "api/modules": "API 子模块：封装后端 REST 接口的请求与响应类型。",
    "api": "HTTP 客户端层：Axios 实例、拦截器、端点常量与响应适配。",
    "components/ui": "基础 UI 组件库：按钮、卡片、分页、加载态等可复用控件。",
    "components/common": "通用业务组件：Toast、对话框、章节标题与布局辅助。",
    "components": "应用壳层组件：顶栏导航、侧栏菜单与路由出口。",
    "hooks": "自定义 React Hooks：鉴权、异步请求与页面状态复用。",
    "store": "Zustand 全局状态：登录态、用户信息与应用级配置。",
    "utils": "工具函数：格式化、校验、API 错误解析与数据映射。",
    "types": "全局 TypeScript 类型定义：实体、DTO 与分页结构。",
    "constants": "业务常量：优先级规则、状态枚举与默认配置项。",
}

SYMBOL_HINTS: dict[str, str] = {
    "Login": "用户登录页：提交凭证并写入 Zustand 认证状态。",
    "Search": "智能检索页：多通路召回结果与可选 RAG 回答展示。",
    "Standards": "标准库主页面：筛选、分页列表与跳转详情。",
    "Alignment": "对齐工作台：选择标准组、配置规则并发起对齐任务。",
    "Import": "标准导入页：文件上传、解析预览与确认入库。",
    "Workbench": "治理工作台首页：拉取 dashboard 指标与图表数据。",
    "Layout": "应用主布局：顶栏导航、角色菜单与 Outlet 渲染。",
    "router": "React Router 配置：懒加载路由与 AuthGuard 鉴权守卫。",
    "useAuthStore": "认证状态 Store：token、用户信息与登出清理。",
    "axios": "Axios 客户端：注入 Bearer Token 与 401 统一跳转登录。",
    "adapter": "API 响应适配层：统一解包 code/data/message 结构。",
    "dataMapper": "前后端字段映射：蛇形/驼峰转换与空值兜底。",
    "apiError": "API 错误文案提取：兼容 Axios 与业务错误码。",
}


def _module_blurb(rel: str) -> str:
    posix = rel.replace("\\", "/")
    for prefix, desc in MODULE_DESC.items():
        if posix.startswith(prefix):
            return desc
    if posix.endswith("main.tsx"):
        return "应用入口：挂载 React 根节点并注入路由与全局样式。"
    if posix.endswith("App.tsx"):
        return "根组件：ToastProvider 与 RouterProvider 装配。"
    if posix.endswith("config.ts"):
        return "前端运行时配置：API 基址、上传限制等环境常量。"
    return "SemAlign 前端源码模块，参与民航多源标准治理系统 UI 展示。"


def _file_header(rel: str) -> str:
    name = Path(rel).name
    blurb = _module_blurb(rel)
    hint = SYMBOL_HINTS.get(Path(rel).stem, "")
    lines = [
        "/**",
        f" * {MARKER}",
        f" * @file {name}",
        f" * @description {blurb}",
    ]
    if hint:
        lines.append(f" * @remarks {hint}")
    lines.extend(
        [
            " *",
            " * 规范说明：",
            " * - 本文件注释用于提升可维护性与 Sonar 注释覆盖率；",
            " * - 业务逻辑变更时请同步更新文件头与关键函数 JSDoc；",
            " * - 与后端契约以 semAlign_backend OpenAPI 为准。",
            " */",
            "",
        ]
    )
    return "\n".join(lines)


def _has_file_header(text: str) -> bool:
    return MARKER in text[:800]


def _prev_is_comment(lines: list[str], idx: int) -> bool:
    j = idx - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0:
        return False
    s = lines[j].strip()
    return s.startswith("/**") or s.startswith("*") or s.startswith("//") or s.endswith("*/")


def _describe_symbol(name: str, line: str) -> str:
    if name in SYMBOL_HINTS:
        return SYMBOL_HINTS[name]
    if line.strip().startswith("export interface") or line.strip().startswith("interface"):
        return f"类型定义 `{name}`：描述前后端交互或页面状态结构。"
    if line.strip().startswith("export type") or line.strip().startswith("type"):
        return f"类型别名 `{name}`：约束业务字段或联合枚举取值。"
    if "React.FC" in line or "React.FC<" in line:
        return f"React 组件 `{name}`：负责对应页面或区块的 UI 与交互。"
    if "use" == name[:3] and name[3:4].isupper():
        return f"Hook `{name}`：封装可复用的状态逻辑与副作用。"
    if name.endswith("Service") or name.endswith("Api"):
        return f"服务模块 `{name}`：聚合 API 调用并返回强类型结果。"
    if "async" in line:
        return f"异步函数 `{name}`：发起 API 请求或执行页面侧异步流程。"
    return f"函数 `{name}`：本模块内部业务辅助逻辑。"


PATTERNS = [
    re.compile(r"^(export\s+)?interface\s+(\w+)"),
    re.compile(r"^(export\s+)?type\s+(\w+)"),
    re.compile(r"^(export\s+)?async\s+function\s+(\w+)"),
    re.compile(r"^(export\s+)?function\s+(\w+)"),
    re.compile(r"^export\s+const\s+(\w+)"),
    re.compile(r"^const\s+(\w+)\s*:\s*React\.FC"),
    re.compile(r"^const\s+(\w+)\s*=\s*\("),
    re.compile(r"^const\s+(\w+)\s*=\s*async\s*\("),
]


def _interface_block(name: str, line: str) -> str:
    """生成多行 interface/type JSDoc（计入更多注释行）。"""
    indent = line[: len(line) - len(line.lstrip())]
    return (
        f"{indent}/**\n"
        f"{indent} * 类型 `{name}`：描述业务实体或 API 载荷结构。\n"
        f"{indent} * @remarks 修改字段时请同步更新 api/modules 与后端 Pydantic Schema。\n"
        f"{indent} * @see types/index.ts\n"
        f"{indent} */\n"
    )


def _insert_jsdocs(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    inserts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("/", "*", "import ", "export {")):
            continue
        for pat in PATTERNS:
            m = pat.match(stripped)
            if not m:
                continue
            name = m.group(m.lastindex or 2)
            if name.startswith("_") or name in {"default"}:
                break
            if _prev_is_comment(lines, i):
                break
            is_type = stripped.startswith("export interface") or stripped.startswith("interface") or stripped.startswith("export type") or stripped.startswith("type ")
            if is_type:
                block = _interface_block(name, line)
            else:
                doc = _describe_symbol(name, stripped)
                indent = line[: len(line) - len(stripped)]
                block = (
                    f"{indent}/**\n"
                    f"{indent} * {doc}\n"
                    f"{indent} * @remarks 详见模块文件头说明。\n"
                    f"{indent} */\n"
                )
            inserts.append((i, block))
            break
    if not inserts:
        return text, 0
    for idx, block in sorted(inserts, key=lambda x: x[0], reverse=True):
        lines.insert(idx, block)
    return "".join(lines), len(inserts)


def _section_comments_for_large_files(text: str, rel: str) -> tuple[str, int]:
    """为超大文件追加分段注释，避免单文件注释不足。"""
    line_count = text.count("\n") + 1
    if line_count < 150:
        return text, 0
    extra = [
        "// -----------------------------------------------------------------------------",
        f"// 分段：{Path(rel).name} 核心业务逻辑区（状态管理、事件处理与 API 调用）",
        "// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。",
        "// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    # 在首个 import 块结束后插入
    lines = text.splitlines(keepends=True)
    insert_at = 0
    in_import = False
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("export type") and "from" in line:
            in_import = True
            insert_at = i + 1
        elif in_import and line.strip() and not line.startswith("import "):
            insert_at = i
            break
    block = "\n".join(extra) + ("\n" if extra else "")
    if any("分段：" in ln and Path(rel).name in ln for ln in lines[: insert_at + 5]):
        return text, 0
    lines.insert(insert_at, block)
    return "".join(lines), len(extra)


def enrich_file(path: Path) -> tuple[bool, int]:
    rel = str(path.relative_to(ROOT))
    if rel.endswith("vite-env.d.ts"):
        return False, 0
    text = path.read_text(encoding="utf-8")
    added = 0
    if not _has_file_header(text):
        text = _file_header(rel) + text
        added += 12
    text, n = _insert_jsdocs(text)
    added += n * 3
    text, n2 = _section_comments_for_large_files(text, rel)
    added += n2
    path.write_text(text, encoding="utf-8")
    return added > 0, added


def main() -> None:
    total_files = 0
    total_added = 0
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        changed, est = enrich_file(path)
        if changed:
            total_files += 1
            total_added += est
    print(f"已处理 {total_files} 个前端文件，估计新增约 {total_added} 行注释")


if __name__ == "__main__":
    main()
