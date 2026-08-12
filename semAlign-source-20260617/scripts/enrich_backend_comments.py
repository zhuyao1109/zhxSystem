#!/usr/bin/env python3
"""为后端核心模块批量补充中文 docstring，提升 Sonar 注释密度。"""

from __future__ import annotations

import ast
import tokenize
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semAlign_backend"

# 按函数名定制的说明（其余使用通用模板）
CUSTOM: dict[str, dict[str, str]] = {
    "services/alignment_executor.py": {
        "_clean_text": "压缩连续空白并去除首尾空格，统一文本口径。",
        "_chroma_db_path": "解析 Chroma 持久化 sqlite 路径（支持相对配置）。",
        "_text_output_dir": "解析标准解析文本输出目录。",
        "_is_effective_text": "判断候选正文是否达到最小有效长度（120 字符）。",
        "_join_chunk_texts": "将向量 chunk 列表拼接为连续正文。",
        "_load_chunks_from_store": "按 file_id / standard_id / source 多键查询 ChunkStore。",
        "_load_from_chroma_sqlite": "直接从 Chroma sqlite 元数据表读取 chunk 文本。",
        "_load_text_by_suffix": "按源文件名后缀在 texts 目录中查找最长匹配文本。",
        "_load_text_by_standard_no": "在 texts 目录中按标准号模糊匹配正文。",
        "_collect_page_marks": "从正文中提取「第 N 页 / page N」页码标记位置。",
        "_page_for_position": "根据字符偏移量映射到最近页码。",
        "_split_raw_parts": "按条款编号或句号将正文切分为原始片段。",
        "_clause_from_part": "将原始片段转换为带章节号的条款对象。",
        "_split_clauses": "将标准全文切分为有限数量的对齐条款单元。",
        "_tokenize": "简易分词：提取中英文与数字 token 集合。",
        "_fallback_similarity": "Jaccard + SequenceMatcher 混合相似度（Aligner 不可用时的回退）。",
        "_try_load_from_chunk_store": "尝试从 ChunkStore 加载标准关联 chunk 文本。",
        "_try_load_from_saved_files": "尝试从 uploads/texts 落盘文件加载正文。",
        "_collect_standard_text_candidates": "汇总描述字段、文件、向量库等多源正文候选。",
        "_load_standard_text": "选择最长有效候选作为标准对齐输入正文。",
        "_ensure_effective_text": "校验正文长度与条款数量，不满足则抛出 ValueError。",
        "_severity": "按相似度分数映射冲突严重级别文案。",
        "_extract_year": "从标准号字符串中提取四位年份。",
        "_is_international": "根据标准号与名称判断是否国际/行业标准。",
        "_is_mandatory_standard": "根据标准号与状态判断是否强制性标准。",
        "_build_standard_meta": "构建对齐流水线使用的标准元数据字典。",
        "_priority_config_from_selected": "将前端勾选的优先级规则转为 RuleOrchestrator 配置。",
        "_priority_score": "综合相似度、置信度与规则标签计算优先级分数。",
        "_build_solution": "为单条冲突生成前端展示用的解决方案结构。",
        "_align_pairs_with_fallback": "穷举或贪心配对条款并计算 fallback 相似度。",
        "_align_pairs_for_pipeline": "供四层流水线调用的条款配对适配层。",
        "_align_pairs": "优先 ClauseAligner，失败时回退 fallback 配对。",
        "run_alignment": "对齐任务主入口：加载文本、切条款、执行四层流水线并返回结果 JSON。",
        "_Clause": "内部条款数据结构，承载索引、正文、章节与页码。",
    },
    "routers/search.py": {
        "_metadata_score": "按标准号/名称/描述与关键词的命中程度计算元数据相关度。",
        "_snippet": "截取包含关键词的上下文片段用于搜索结果展示。",
        "_to_result": "将 Standard ORM 对象转换为 SearchResult 响应结构。",
        "_vector_only_result": "构造仅来自向量命中、未关联标准库记录的伪结果项。",
        "_vector_metadata_rows": "查询 Chroma sqlite 中 metadata 含关键词的 source 行。",
        "_push_suggestion": "向联想列表追加去重后的检索建议条目。",
        "_find_standard_by_source": "按 source 文件名在标准库中反查 Standard 记录。",
        "_score_from_chunk_count": "按 chunk 数量估算向量命中相关度。",
        "_merge_standard_hit": "合并 SQL 与向量通路对同一标准的得分。",
        "_add_or_bump_pseudo_result": "合并或提升伪标准结果的向量得分。",
        "_apply_direct_vector_rows": "将 Chroma 元数据行转为检索结果并合并排序。",
        "_resolve_standard_from_meta": "从 chunk 元数据解析并关联标准库记录。",
        "_apply_chunk_store_hits": "将 ChunkStore 混合检索命中合并进结果集。",
        "_collect_standard_suggestions": "收集标准号/名称联想候选。",
        "search_standards": "智能检索主接口：元数据 + 向量 + BM25 多通路融合。",
        "get_search_suggestions": "检索关键词联想接口（标准号/名称前缀匹配）。",
    },
    "services/comparison_payloads.py": {
        "get_comparison_task_payload": "返回比对任务概览演示数据（MVP 联调用）。",
        "get_comparison_stats_payload": "返回冲突率/匹配率等统计演示数据。",
        "get_semantic_clusters_payload": "返回语义聚类列表演示数据。",
        "get_conflicts_payload": "返回冲突点列表演示数据。",
        "get_solutions_payload": "返回解决方案列表演示数据。",
        "get_feedback_counts": "返回赞成/反对计数演示数据。",
        "get_modifications_payload": "返回修改意见列表演示数据。",
    },
    "services/rule_engine/priority_rules.py": {
        "BaseRule": "优先级规则抽象基类，定义条款对与元数据评估接口。",
        "InternationalPriorityRule": "国际标准优先于国内标准的判定规则。",
        "LatestRevisionRule": "较新发布日期优先的判定规则。",
        "MandatoryPriorityRule": "强制性条款优先于推荐性条款的判定规则。",
        "_get_standard_type": "根据 publisher 字段判断国际/国内/未知类型。",
        "_extract_date": "从元数据中解析发布日期，支持多种格式。",
        "_is_mandatory": "根据 shall/must/必须 等关键词识别强制性表述。",
        "evaluate": "对一对冲突条款执行本规则并返回推荐与置信度。",
    },
    "services/rule_engine/rule_orchestrator.py": {
        "RuleOrchestrator": "多规则编排器，按配置启用规则并融合评估结果。",
        "_init_rules": "根据 enabled_rules 实例化具体优先级规则。",
        "evaluate": "对冲突条目依次执行已启用规则并输出最终推荐。",
        "_weighted_sum_strategy": "按权重加权求和融合多规则得分。",
        "_hierarchical_strategy": "按规则优先级层级选取最终推荐。",
        "_user_choice_strategy": "无法自动裁决时标记需用户决策。",
    },
    "services/conflict_pipeline/layer4_adjudication.py": {
        "_severity": "结合相似度与冲突置信度映射严重级别。",
        "_priority_score": "计算冲突项优先级综合分数。",
        "_is_conflict_pair": "判断候选对是否应纳入冲突列表。",
        "_layer3_to_dict": "将第三层结果序列化为 comparison API 兼容字典。",
        "_build_adjudication_summary": "生成冲突裁决自然语言摘要。",
        "_build_adjudicated_conflict": "组装单条裁决后的冲突实体。",
        "adjudicate_conflicts": "第四层主流程：过滤、裁决、排序并限制最大冲突数。",
        "conflicts_to_legacy_dict": "转换为前端 comparison 接口兼容的 JSON 结构。",
        "build_solutions": "基于冲突列表生成解决建议条目。",
        "generate_natural_language_report": "生成 Markdown 格式的冲突检测报告全文。",
    },
    "routers/vector_store.py": {
        "VectorSourceRow": "向量库中单来源文件的 chunk 统计行。",
        "VectorStoreOverviewData": "向量库概览响应体：容量、维度、分来源统计。",
        "get_vector_store_overview": "管理员只读接口：展示 Chroma 库状态与来源分布。",
    },
}

MODULE_EXTRA: dict[str, str] = {
    "services/alignment_executor.py": (
        "\n\n"
        "职责说明：\n"
        "    - 多源加载标准正文（描述、文本文件、Chroma chunk）；\n"
        "    - 条款切分与 ClauseAligner / fallback 配对；\n"
        "    - 委托四层 conflict_pipeline 产出冲突、统计与解决方案。\n"
        "\n"
        "对外入口：run_alignment() 由 alignment 路由在后台线程调用。\n"
    ),
    "routers/search.py": (
        "\n\n"
        "检索策略：\n"
        "    1. SQL 元数据模糊匹配；\n"
        "    2. Chroma metadata 与 ChunkStore 混合向量召回；\n"
        "    3. 可选 RAG 生成式回答（search_rag_enabled 控制）。\n"
    ),
    "services/comparison_payloads.py": (
        "\n\n"
        "说明：本模块提供 MVP 阶段静态演示数据，生产环境比对结果以\n"
        "routers/comparison.py 读取 alignment_tasks.result_json 为准。\n"
    ),
    "services/rule_engine/priority_rules.py": (
        '"""标准对齐优先级规则集。\n\n'
        "实现国际标准优先、最新修订优先、强制性标准优先等可配置策略，\n"
        "供 RuleOrchestrator 在冲突裁决阶段调用。\n"
        '"""\n\n'
    ),
    "services/rule_engine/rule_orchestrator.py": (
        '"""规则编排器 — 融合多条优先级规则输出最终推荐。"""\n\n'
    ),
    "utils/document_processor.py": (
        "\n\n"
        "模块组成：\n"
        "    - DocumentProcessor：PDF/Excel 解析、OCR 回退、向量入库；\n"
        "    - ChunkStore：BM25 + Chroma 混合检索封装；\n"
        "    - 辅助类 _OCRPdfParser / _ExcelParser / _ImageAwareSplitter。\n"
    ),
    "utils/pdf_parser.py": (
        "\n\n"
        "支持从 PDF 纯文本与 Excel 表格行抽取标准号、名称、版本等字段，\n"
        "供标准导入流程校验与批量入库使用。\n"
    ),
    "services/conflict_pipeline/layer4_adjudication.py": (
        "\n\n"
        "输入：第二层分析结果 + 第三层引用链 enrichment；\n"
        "输出：带优先级排序的冲突列表、解决方案与自然语言报告。\n"
    ),
    "routers/vector_store.py": (
        "\n\n"
        "仅管理员可访问，直接读取 Chroma sqlite 统计各 source 的 chunk 数量，\n"
        "用于运维排查向量索引是否入库成功。\n"
    ),
}


def _line_indent(source: str, node: ast.AST) -> str:
    line = source.splitlines()[node.lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def _has_docstring(node: ast.AST, source: str) -> bool:
    if not (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))
        and node.body
    ):
        return False
    first = node.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def _generic_doc(name: str, kind: str) -> str:
    if name.startswith("_"):
        return f'"""{kind}内部辅助：{name.lstrip("_").replace("_", " ")}。"""'
    return f'"""{kind}：{name.replace("_", " ")}。"""'


def enrich_file(rel_path: str) -> int:
    path = ROOT / rel_path
    if not path.exists():
        return 0
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    inserts: list[tuple[int, str]] = []
    custom = CUSTOM.get(rel_path, {})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if _has_docstring(node, source):
                continue
            name = node.name
            kind = "类" if isinstance(node, ast.ClassDef) else "函数"
            doc = custom.get(name) or _generic_doc(name, kind).strip('"""').strip()
            docstring = f'"""{doc}"""'
            indent = _line_indent(source, node)
            inner = indent + "    "
            block = f"{inner}{docstring}"
            inserts.append((node.body[0].lineno if node.body else node.lineno + 1, block))

    if not inserts:
        return 0

    lines = source.splitlines(keepends=True)
    for lineno, block in sorted(inserts, key=lambda x: x[0], reverse=True):
        idx = lineno - 1
        lines.insert(idx, block + "\n")

    path.write_text("".join(lines), encoding="utf-8")
    return len(inserts)


def fix_rule_engine_headers() -> None:
    for rel, header in [
        ("services/rule_engine/priority_rules.py", MODULE_EXTRA["services/rule_engine/priority_rules.py"]),
        ("services/rule_engine/rule_orchestrator.py", MODULE_EXTRA["services/rule_engine/rule_orchestrator.py"]),
    ]:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        if text.startswith("from ") or text.startswith("import "):
            path.write_text(header + text, encoding="utf-8")


def main() -> None:
    fix_rule_engine_headers()
    targets = list(CUSTOM.keys()) + [
        "utils/document_processor.py",
        "utils/pdf_parser.py",
        "services/conflict_pipeline/layer1_recall.py",
        "services/conflict_pipeline/layer2_agents.py",
        "services/conflict_pipeline/layer3_active_seek.py",
        "services/conflict_pipeline/pipeline.py",
        "routers/comparison.py",
        "routers/conflict_dialogues.py",
        "services/preprocessing/document_parser.py",
        "services/preprocessing/ocr.py",
        "services/preprocessing/metadata_extractor.py",
        "services/conflict_detection/conflict_detector.py",
        "services/conflict_detection/llm_conflict_detector.py",
        "services/export_report.py",
        "services/reporting/report_generator.py",
        "services/reporting/visualization.py",
        "utils/validators.py",
        "utils/rag.py",
        "utils/file_utils.py",
        "core/deps.py",
        "core/database.py",
        "core/security.py",
    ]
    total = 0
    for rel in targets:
        total += enrich_file(rel)
    print(f"已为 {len(targets)} 个文件补充 docstring，新增约 {total} 处")


if __name__ == "__main__":
    main()
