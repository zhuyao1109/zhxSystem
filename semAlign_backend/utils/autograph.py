"""
utils/autograph.py
------------------
AutoGraph:图增强的 agent 式 RAG(方案 A,保留知识图谱 + 实体抽取)。

流程:
  查询分析(规则)→ 查询分解(≤2)→ 多路径检索 → 实体/关系抽取建图
  → 迭代工具调用(≤4 轮:Graph_Search / Expand_Node / Verify_Relation
    / Synthesize_Evidence / Answer_and_Halt)→ 证据合成 → 最终回答。

简化 / 提速:
  - 查询分解最多 2 个子查询(原 3)。
  - 主循环最多 4 轮迭代(原 8)。
  - 删除全部消融分支(no_tools / no_analysis / no_graph)。
  - 删除社区检测 / 社区摘要(每轮额外 LLM 调用 + 线程),提速。
  - 删除 TaskPromptGenerator 与 QueryAnalyzer 的 LLM 兜底(只保留规则分析),减少 LLM 往返。
  - PROMPTS 内联;复用 get_chunk_store() 作为 retriever,不自建 FAISS。

中文:所有内部中间产物(实体抽取、关系、证据合成、最终回答)均强制【简体中文】。
"""
import re
import json
import math
import hashlib
import concurrent.futures
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, List

from utils.rag_common import (
    BaseRAG, RAGResult, Turn, register,
    get_llm, retrieve_chunks, extract_context,
)

import os
import logging

logger = logging.getLogger(__name__)

# ================================================================== #
# 内联 PROMPTS(全部中文化;删除 no_graph 等消融相关模板)
# ================================================================== #
TUPLE_DELIM = "<|#|>"
COMPLETE_DELIM = "<|COMPLETE|>"

RELATION_VOCAB = {
    "analytical": ["increases", "decreases", "predicts", "correlates_with",
                   "depends_on", "interacts_with", "part_of",
                   "trained_on", "measured_by", "optimized_by"],
    "compliance": ["regulates", "requires_compliance", "grants_approval",
                   "submits_to", "part_of", "depends_on",
                   "defines", "prohibits", "enables", "violates"],
    "general": ["causes", "enables", "inhibits", "part_of", "precedes",
                "supports", "contradicts", "related_to", "defines", "located_in"],
}

# 实体抽取 system —— 要求用中文输出描述
ENTITY_EXTRACTION_SYSTEM = """\
---角色---
你是知识图谱专家,负责从输入文本中抽取实体与关系。

---要求---
1. 从文本中抽取实体。实体名请从原文精确复制(不要改写)。
   格式:entity{td}名称{td}类型{td}描述
2. 关系关键词必须严格取自下方受控词表中的某一个英文术语。
   格式:relation{td}源实体{td}目标实体{td}关键词{td}描述
3. 受控关系词表(必须使用其中之一):
   {vocab}
4. 规则:{td} 为原子分隔符,不可出现在字段内部。不要重复。先输出所有实体,再输出所有关系。
   使用第三人称。所有【描述】必须使用【简体中文】撰写,简洁且信息量高,聚焦与问题的相关性。
   结尾输出:{cd}
"""

# 实体抽取 user
ENTITY_EXTRACTION_USER = """\
---查询上下文---
用户正在问:"{query}"
证据模式:{mode_label}
优先抽取这些类型的实体:[{focus_types}]

不仅要抽取问题中显式提到的实体,也要抽取多跳推理中可能起桥接作用的实体。
宁可多抽,不要漏抽。所有实体【描述】必须用【简体中文】。
可用实体类型:[{entity_types}]
结尾输出:{cd}
---输入---
```
{input_text}
```
---输出---
"""

# 证据合成 —— 要求中文
SYNTHESIZE_EVIDENCE = """\
---角色---
你是证据分析师。请依据下方来源片段抽取并组织证据,输出将用于最终回答,请全面并为每条主张标注来源。
【必须使用简体中文输出。】

---规则---
1. 每条事实性主张都要引用下方带编号的片段,编号需与片段对应。
2. 若某事实仅来自知识图谱(而非片段),标注"(来自图谱)"。
3. 不要编造事实。缺乏支撑的内容放入 ## 缺口。
4. 结尾用 ## 缺口 列出证据未覆盖的内容。
5. 再用 ## 参考 列出每个被引用的片段编号及这个chunk的内容概括。

---关注点---
{focus}

---知识图谱上下文---
{context_data}
"""

# 最终回答 —— 要求中文
RAG_RESPONSE = """\
---角色---
你是 RAG 助手。请依据下方的证据报告,用【简体中文】写出清晰、结构化的回答。

---规则---
- 每条事实性主张都要引用证据报告中的编号或图谱上下文。
- 不要引入证据报告中不存在的事实。
- 如果证据与问题无关,只回复:"上下文中不包含相关信息"。
"""

# Agent 系统提示(保留图谱版;中文说明)
AGENT_SYSTEM = """\
你是 AutoGraph,一个实时图增强推理 agent。请使用工具对检索到的证据做更深入的理解与综合。

## 记忆结构
1. 局部子图 —— 语义检索到的实体与直接关系。

## 工作流
1. Graph_Search        → 检索文档、构建图、返回增量。
2. Expand_Node         → 深入某个实体。
3. Verify_Relation     → 确认两个实体间的联系。
4. Synthesize_Evidence → 停止前必须调用。
5. Answer_and_Halt     → 生成最终回答。

## 每次调用工具前
用 1~2 句(中文)说明:子图揭示了什么 + 还有什么缺口。

## 规则
- 最终回答必须通过 Answer_and_Halt。
- 不要用自然语言直接回答 —— 始终通过工具调用。
- 在 Answer_and_Halt 之前,必须至少调用一次 Expand_Node 或 Verify_Relation。
- 检索类动作总数最多 4 次。

## 停止条件
- 子图中已有 10 个以上带摘要的实体。
- 上一次增量为空。
- 检索动作已用尽。
"""

# ================================================================== #
# 工具函数
# ================================================================== #
def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\w]+", text.lower())

def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def _safe_json_loads(text: str, default):
    try:
        return json.loads(_strip_code_fences(text))
    except Exception:
        return default

def _chat(messages, model, temperature=0.3, max_tokens=1200, tools=None,
          tool_choice=None):
    """统一的同步 chat 调用(复用 rag_common 的 LLM 单例)。"""
    kwargs = dict(model=model, messages=messages,
                  temperature=temperature, max_tokens=max_tokens)
    if tools is not None:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    return get_llm().chat.completions.create(**kwargs)

# ================================================================== #
# BM25 重排(轻量)
# ================================================================== #
class _BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b

    def rank(self, query: str, docs: List[str], top_k: int = 10) -> List[str]:
        if not docs:
            return []
        tok = [_tokenize(d) for d in docs]
        N = len(docs)
        df = defaultdict(int)
        for toks in tok:
            for t in set(toks):
                df[t] += 1
        idf = {t: math.log((N - n + 0.5) / (n + 0.5) + 1) for t, n in df.items()}
        avg_dl = sum(len(t) for t in tok) / max(N, 1)
        q = _tokenize(query)
        if not q:
            return docs[:top_k]
        scored = []
        for toks, doc in zip(tok, docs):
            dl = len(toks)
            freq = defaultdict(int)
            for t in toks:
                freq[t] += 1
            sc = 0.0
            for qt in q:
                f = freq.get(qt, 0)
                if not f:
                    continue
                tf = f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / max(avg_dl, 1e-9)))
                sc += idf.get(qt, 1.0) * tf
            scored.append((sc, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:top_k]]

# ================================================================== #
# 关系归一化
# ================================================================== #
class _RelationNormalizer:
    _ALIAS = {
        "affects": "correlates_with", "influences": "correlates_with",
        "uses": "depends_on", "requires": "depends_on",
        "is_part_of": "part_of", "belongs_to": "part_of",
    }

    def __init__(self, vocab: List[str]):
        self._vocab = vocab
        self._set = set(vocab)

    def normalize(self, raw: str) -> str:
        kw = (raw or "").strip().lower().replace(" ", "_")
        if kw in self._set:
            return kw
        if kw in self._ALIAS and self._ALIAS[kw] in self._set:
            return self._ALIAS[kw]
        kw_t = set(kw.split("_"))
        best, best_sc = (self._vocab[0] if self._vocab else "related_to"), 0.0
        for v in self._vocab:
            vt = set(v.split("_"))
            sc = len(kw_t & vt) / max(len(kw_t | vt), 1)
            if sc > best_sc:
                best, best_sc = v, sc
        return best

# ================================================================== #
# 查询分析(仅规则,无 LLM 兜底 —— 提速)
# ================================================================== #
@dataclass
class _Mode:
    mode: str
    label: str
    focus_types: List[str]

_MODE_META = {
    "data_analysis": ("数据分析 / ML", ["Feature", "Target", "Metric", "Model", "Dataset"]),
    "compliance": ("合规", ["Regulation", "Requirement", "Organization", "Artifact", "Event"]),
    "comparative": ("对比分析", ["Concept", "Model", "Method", "Artifact", "Organization"]),
    "causal": ("因果 / 机制", ["Concept", "Feature", "Event", "Method"]),
    "factual": ("事实 / 描述", ["Concept", "Person", "Organization", "Event", "Location"]),
}

_MODE_TO_DOMAIN = {
    "data_analysis": "analytical", "compliance": "compliance",
    "comparative": "general", "causal": "general", "factual": "general",
}

_RULES = [
    ("data_analysis", [r"\bfeature\b", r"\bpredict\b", r"\bmodel\b", r"\bdataset\b",
                       r"\bcorrelat", r"\bregress\b", r"特征", r"预测", r"模型", r"数据集"]),
    ("compliance", [r"\bcompli\w+\b", r"\bregulat\w+\b", r"\blegal\b", r"\baudit\b",
                    r"合规", r"监管", r"法律", r"审计", r"合同"]),
    ("comparative", [r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b", r"对比", r"比较", r"区别"]),
    ("causal", [r"\bwhy\b", r"\bcause", r"\bimpact of\b", r"为什么", r"原因", r"导致", r"影响"]),
    ("factual", [r"\bwhat is\b", r"\bdefine\b", r"\bexplain\b", r"是什么", r"定义", r"解释"]),
]

def _analyze_mode(query: str) -> _Mode:
    q = query.lower()
    raw = defaultdict(float)
    for mode, patterns in _RULES:
        hits = sum(1 for p in patterns if re.search(p, q))
        if hits:
            raw[mode] += hits
    top = max(raw, key=raw.get) if raw else "factual"
    label, focus = _MODE_META[top]
    return _Mode(mode=top, label=label, focus_types=focus)

# ================================================================== #
# 图数据结构
# ================================================================== #
@dataclass
class _Node:
    name: str
    summaries: List[str] = field(default_factory=list)
    hit_count: int = 0

    def add_summary(self, s: str) -> bool:
        if s and s not in self.summaries:
            self.summaries.append(s)
            self.hit_count += 1
            return True
        return False

    def merged(self, max_len: int = 300) -> str:
        m = " | ".join(self.summaries)
        return (m[:max_len] + "...") if len(m) > max_len else m

@dataclass
class _Edge:
    source: str
    relation: str
    target: str
    summaries: List[str] = field(default_factory=list)
    hit_count: int = 0

    def add_summary(self, s: str) -> bool:
        if s and s not in self.summaries:
            self.summaries.append(s)
            self.hit_count += 1
            return True
        return False

class _Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.docs = set()

    def touch_entity(self, name: str, summary: str = ""):
        name = (name or "").strip()
        if not name:
            return False, False, ""
        lower = name.lower()
        for existing in self.nodes:
            if existing.lower() == lower or lower in existing.lower() or existing.lower() in lower:
                enriched = self.nodes[existing].add_summary(summary) if summary else False
                return False, enriched, existing
        self.nodes[name] = _Node(name)
        if summary:
            self.nodes[name].add_summary(summary)
        return True, False, name

    def add_edge(self, source, relation, target, summary=""):
        source, relation, target = (source or "").strip(), (relation or "").strip(), (target or "").strip()
        if not source or not target:
            return False, ("", "", "")
        _, _, cs = self.touch_entity(source)
        _, _, ct = self.touch_entity(target)
        if not cs or not ct:
            return False, ("", "", "")
        key = (cs.lower(), relation.lower(), ct.lower())
        is_new = key not in self.edges
        if is_new:
            self.edges[key] = _Edge(cs, relation, ct)
        if summary:
            self.edges[key].add_summary(summary)
        return is_new, (cs, relation, ct)

    def status(self) -> str:
        return f"Graph({len(self.nodes)} nodes, {len(self.edges)} edges, {len(self.docs)} docs)"

    def prune(self, max_nodes=80, max_edges=120):
        if len(self.nodes) <= max_nodes and len(self.edges) <= max_edges:
            return
        degree = defaultdict(int)
        for e in self.edges.values():
            degree[e.source] += 1
            degree[e.target] += 1
        keep = set(sorted(self.nodes,
                          key=lambda n: self.nodes[n].hit_count * 2 + degree.get(n, 0),
                          reverse=True)[:max_nodes])
        for n in set(self.nodes) - keep:
            del self.nodes[n]
        for k in [k for k, e in self.edges.items() if e.source not in keep or e.target not in keep]:
            del self.edges[k]

# ================================================================== #
# 实体抽取
# ================================================================== #
class _Extractor:
    ALL_TYPES = ["Feature", "Target", "Model", "Dataset", "Metric", "Concept",
                 "Method", "Person", "Organization", "Location", "Event",
                 "Artifact", "Regulation", "Requirement", "Other"]

    def __init__(self, model: str, domain: str = "analytical"):
        self.model = model
        vocab = RELATION_VOCAB.get(domain, RELATION_VOCAB["general"])
        self._norm = _RelationNormalizer(vocab)
        self._vocab_str = " | ".join(vocab)

    def extract(self, chunk: str, query: str, mode: _Mode) -> dict:
        sys_prompt = ENTITY_EXTRACTION_SYSTEM.format(
            td=TUPLE_DELIM, cd=COMPLETE_DELIM, vocab=self._vocab_str)
        user_prompt = ENTITY_EXTRACTION_USER.format(
            query=query, mode_label=mode.label,
            focus_types=", ".join(mode.focus_types),
            entity_types=", ".join(self.ALL_TYPES),
            cd=COMPLETE_DELIM, input_text=chunk[:3000])
        try:
            resp = _chat(
                [{"role": "system", "content": sys_prompt},
                 {"role": "user", "content": user_prompt}],
                model=self.model, temperature=0.3, max_tokens=1200)
            return self._parse(resp.choices[0].message.content or "")
        except Exception as exc:
            logger.warning("[Extractor] %s", exc)
            return {"entities": [], "relations": []}

    def _parse(self, raw: str) -> dict:
        entities, relations = [], []
        stop = raw.find(COMPLETE_DELIM)
        text = raw[:stop] if stop != -1 else raw
        for line in text.splitlines():
            parts = [p.strip() for p in line.strip().split(TUPLE_DELIM)]
            if not parts:
                continue
            if parts[0] == "entity" and len(parts) >= 4:
                entities.append({"name": parts[1], "type": parts[2], "summary": parts[3]})
            elif parts[0] == "relation" and len(parts) >= 5:
                relations.append({"h": parts[1], "t": parts[2],
                                  "r": self._norm.normalize(parts[3]), "summary": parts[4]})
        return {"entities": entities, "relations": relations}

# ================================================================== #
# 工具 Schema
# ================================================================== #
_GRAPH_SEARCH = {"type": "function", "function": {
    "name": "Graph_Search", "description": "检索文档并更新知识图谱。",
    "parameters": {"type": "object", "properties": {
        "queries": {"type": "array", "items": {"type": "string"},
                    "description": "拆解后的检索查询列表。"}}, "required": ["queries"]}}}
_EXPAND_NODE = {"type": "function", "function": {
    "name": "Expand_Node", "description": "深入图中已有的某个实体。",
    "parameters": {"type": "object", "properties": {
        "entity_name": {"type": "string"}}, "required": ["entity_name"]}}}
_VERIFY_RELATION = {"type": "function", "function": {
    "name": "Verify_Relation", "description": "检索同时包含两个实体的文档以验证其关系。",
    "parameters": {"type": "object", "properties": {
        "entity_a": {"type": "string"}, "entity_b": {"type": "string"}},
        "required": ["entity_a", "entity_b"]}}}
_SYNTHESIZE = {"type": "function", "function": {
    "name": "Synthesize_Evidence", "description": "Answer_and_Halt 之前必须调用,构建有据可依的证据。",
    "parameters": {"type": "object", "properties": {
        "focus": {"type": "string"}}, "required": ["focus"]}}}
_ANSWER = {"type": "function", "function": {
    "name": "Answer_and_Halt", "description": "在 Synthesize_Evidence 之后生成最终回答并停止。",
    "parameters": {"type": "object", "properties": {}, "required": []}}}

# ================================================================== #
# AutoGraph 核心引擎
# ================================================================== #
class _AutoGraphEngine:
    def __init__(self, retriever: Callable[[str], List[str]], model: str,
                 top_k: int = 5, max_iterations: int = 4, max_sub_queries: int = 2,
                 max_search_actions: int = 4):
        self.retriever = retriever
        self.model = model
        self.top_k = top_k
        self.max_iterations = max_iterations          # 简化:默认 4 轮
        self.max_sub_queries = max_sub_queries        # 简化:默认 2 个子查询
        self.max_search_actions = max_search_actions

    # ---- 查询分解(≤2) ----
    def _decompose(self, question: str, mode: _Mode) -> List[str]:
        prompt = (
            f"请把用户问题拆解为至多 {self.max_sub_queries} 个互补的检索查询,"
            "每个查询针对不同侧面,避免同义改写。所有查询用【简体中文】。\n"
            '只返回 JSON:{"queries": ["...", "..."]}\n\n'
            f"问题:\n{question}\n证据模式:{mode.label}"
        )
        try:
            resp = _chat([{"role": "user", "content": prompt}],
                         model=self.model, temperature=0.2, max_tokens=200)
            obj = _safe_json_loads(resp.choices[0].message.content, {})
            qs = [q.strip() for q in obj.get("queries", []) if isinstance(q, str) and q.strip()]
            seen, uniq = set(), []
            for q in qs:
                if q.lower() not in seen:
                    uniq.append(q)
                    seen.add(q.lower())
            return uniq[:self.max_sub_queries] or [question]
        except Exception as exc:
            logger.warning("[Decompose] %s", exc)
            return [question]

    # ---- 并行检索 + 去重 ----
    def _parallel_retrieve(self, queries: List[str]) -> List[str]:
        uniq_q = []
        for q in queries:
            q = (q or "").strip()
            if q and q.lower() not in self._searched:
                uniq_q.append(q)
                self._searched.add(q.lower())
        if not uniq_q:
            return []
        all_chunks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(uniq_q), 4)) as ex:
            futs = {ex.submit(self.retriever, q): q for q in uniq_q}
            for fut in concurrent.futures.as_completed(futs):
                try:
                    all_chunks.extend(fut.result()[:self.top_k])
                except Exception as exc:
                    logger.warning("[Retrieve] %s", exc)
        seen, uniq = set(), []
        for c in all_chunks:
            h = hashlib.md5(c.encode()).hexdigest()
            if h not in seen:
                uniq.append(c)
                seen.add(h)
        return uniq

    # ---- 抽取建图 ----
    def _ingest(self, chunks: List[str]) -> int:
        new = []
        for c in chunks:
            h = hashlib.md5(c.encode()).hexdigest()
            if h not in self._seen:
                new.append((h, c))
        if not new:
            return 0
        added = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(self._extractor.extract, c, self.question, self._mode): (h, c)
                    for h, c in new}
            for fut in concurrent.futures.as_completed(futs):
                h, c = futs[fut]
                self._seen.add(h)
                self._graph.docs.add(c)
                try:
                    result = fut.result()
                except Exception:
                    continue
                for ent in result.get("entities", []):
                    if ent.get("name"):
                        is_new, _, _ = self._graph.touch_entity(ent["name"], ent.get("summary", ""))
                        if is_new:
                            added += 1
                for rel in result.get("relations", []):
                    if rel.get("h") and rel.get("r") and rel.get("t"):
                        self._graph.add_edge(rel["h"], rel["r"], rel["t"], rel.get("summary", ""))
        return added

    # ---- 从图 + 文档构建上下文(BM25 重排) ----
    def _build_context(self, query: str):
        docs = list(self._graph.docs)
        top_chunks = self._bm25.rank(query, docs, top_k=self.top_k * 2) if docs else []

        ent_sorted = sorted(self._graph.nodes.values(), key=lambda n: n.hit_count, reverse=True)[:20]
        e_lines = []
        for node in ent_sorted:
            desc = node.merged(300)
            freq = f" [x{node.hit_count}]" if node.hit_count > 1 else ""
            e_lines.append(f"{node.name.upper()}{freq}. {desc}" if desc else f"{node.name.upper()}{freq}.")

        display_set = {n.name for n in ent_sorted}
        r_lines = []
        for e in sorted([e for e in self._graph.edges.values()
                         if e.source in display_set or e.target in display_set],
                        key=lambda e: e.hit_count, reverse=True)[:30]:
            desc = e.summaries[0][:150] if e.summaries else f"({e.relation})"
            r_lines.append(f"{e.source.upper()} -> {e.target.upper()}. {desc}")

        src_lines = [f"[{i}] {c[:1000].replace(chr(10), ' ').strip()} ..."
                     for i, c in enumerate(top_chunks, 1)] or ["(无来源文档)"]

        ctx = (f"-----实体-----\n{chr(10).join(e_lines) or '(暂无实体)'}\n"
               f"-----关系-----\n{chr(10).join(r_lines) or '(无)'}\n"
               f"-----TopK 片段-----\n{chr(10).join(src_lines)}")
        return ctx, top_chunks

    # ---- 证据合成 ----
    def _synthesize(self, question: str, focus: str) -> str:
        ctx, _ = self._build_context(question)
        print(f"[AutoGraph] 证据合成上下文:\n{ctx}\n")
        prompt = SYNTHESIZE_EVIDENCE.format(focus=focus, context_data=ctx)
        try:
            resp = _chat([{"role": "user", "content": prompt}],
                         model=self.model, temperature=0.3, max_tokens=4000)
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            return f"证据合成失败:{exc}"

    # ---- 最终回答 ----
    def _final_answer(self, question: str) -> str:
        if not self._evidence:
            self._evidence = self._synthesize(question, question)
        print(f"[AutoGraph] 证据合成:\n{self._evidence}\n")
        user_prompt = (
            f"问题:{question}\n\n"
            f"## 证据报告\n{self._evidence}\n\n"
            "请在回答末尾加上 ## 参考,给出对上下文(片段或图谱)的明确引用。"
        )
        try:
            resp = _chat(
                [{"role": "system", "content": RAG_RESPONSE},
                 {"role": "user", "content": user_prompt}],
                model=self.model, temperature=0.3, max_tokens=4000)
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            return f"回答生成失败:{exc}"

    # ---- 可用工具 ----
    def _tools(self):
        tools = [_GRAPH_SEARCH, _EXPAND_NODE, _VERIFY_RELATION]
        if self._stats["expand"] > 0 or self._stats["verify"] > 0:
            tools.append(_SYNTHESIZE)
        if self._evidence:
            tools.append(_ANSWER)
        return tools

    def _sys(self, question: str) -> str:
        base = AGENT_SYSTEM
        if self._evidence:
            base += f"\n\n## 已合成证据\n{self._evidence}"
        if self._graph.nodes or self._graph.docs:
            ctx, _ = self._build_context(question)
            base += f"\n\n## 当前上下文\n{ctx}"
        base += (f"\n\n## 工具状态\nGraph_Search:{self._stats['search']} "
                 f"Expand:{self._stats['expand']} Verify:{self._stats['verify']} "
                 f"Synthesize:{self._stats['synthesize']}")
        return base

    def _think_then_tool(self, messages):
        think = _chat(messages, model=self.model, temperature=0.3, max_tokens=400)
        think_content = (think.choices[0].message.content or "").strip()
        act = list(messages)
        if think_content:
            act.append({"role": "assistant", "content": think_content})
        act.append({"role": "user", "content": "基于以上分析,现在请调用一个或多个工具。不允许重复调用相同工具搜索相同内容"})
        resp = _chat(act, model=self.model, temperature=0.0, max_tokens=512,
                     tools=self._tools(), tool_choice="required")
        return think_content, resp.choices[0].message

    def _trim(self, messages, max_turns=3):
        history = messages[2:]
        limit = max_turns * 2
        if len(history) > limit:
            history = history[-limit:]
        while history and history[0].get("role") == "tool":
            history = history[1:]
        return messages[:2] + history

    # ---- 主入口 ----
    def query(self, question: str) -> str:
        self.question = question
        self._graph = _Graph()
        self._seen = set()
        self._searched = set()
        self._evidence = ""
        self._bm25 = _BM25()
        self._stats = {"search": 0, "expand": 0, "verify": 0, "synthesize": 0}

        self._mode = _analyze_mode(question)
        domain = _MODE_TO_DOMAIN.get(self._mode.mode, "general")
        self._extractor = _Extractor(self.model, domain)

        # bootstrap:分解 + 检索 + 建图
        boot_qs = self._decompose(question, self._mode)
        self._ingest(self._parallel_retrieve(boot_qs))
        self._stats["search"] += 1

        answer = None
        messages = [
            {"role": "system", "content": self._sys(question)},
            {"role": "user", "content": f"问题:{question}"},
        ]

        for _ in range(self.max_iterations):
            messages[0]["content"] = self._sys(question)
            messages = self._trim(messages)
            think, msg = self._think_then_tool(messages)
            print(f"[AutoGraph] ITERATION {_+1} 思考:\n{think}\n")

            am = {"role": "assistant", "content": think or (msg.content or "")}
            if msg.tool_calls:
                am["tool_calls"] = [{
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                } for tc in msg.tool_calls]
            messages.append(am)

            halted = False
            for tc in (msg.tool_calls or []):
                name = tc.function.name
                args = _safe_json_loads(tc.function.arguments, {})
                print(f"[AutoGraph] 工具调用:{name} {args}")

                if name == "Answer_and_Halt":
                    if not self._evidence:
                        messages.append({"role": "tool", "tool_call_id": tc.id,
                                         "content": "错误:必须先调用 Synthesize_Evidence。"})
                        continue
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": "正在生成最终回答。"})
                    answer = self._final_answer(question)
                    halted = True
                    break

                elif name == "Synthesize_Evidence":
                    if self._stats["expand"] == 0 and self._stats["verify"] == 0:
                        messages.append({"role": "tool", "tool_call_id": tc.id,
                                         "content": "错误:必须先调用 Expand_Node 或 Verify_Relation。"})
                        continue
                    self._evidence = self._synthesize(question, args.get("focus", question))
                    self._stats["synthesize"] += 1
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": f"[证据已就绪]\n{self._evidence}"})

                elif name == "Graph_Search":
                    if self._stats["search"] >= self.max_search_actions:
                        messages.append({"role": "tool", "tool_call_id": tc.id,
                                         "content": "检索次数已用尽。"})
                        continue
                    qs = args.get("queries", [])
                    if isinstance(qs, str):
                        qs = [qs]
                    chunks = self._parallel_retrieve(qs)
                    self._stats["search"] += 1
                    self._ingest(chunks)
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": f"检索到 {len(chunks)} 个片段。{self._graph.status()}"})

                elif name == "Expand_Node":
                    entity = args.get("entity_name", "")
                    chunks = self._parallel_retrieve([f"{entity} 机制", f"{entity} 对 {question} 的影响"])
                    self._stats["expand"] += 1
                    self._ingest(chunks)
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": f"已扩展 {entity},新增 {len(chunks)} 个片段。{self._graph.status()}"})

                elif name == "Verify_Relation":
                    a, b = args.get("entity_a", ""), args.get("entity_b", "")
                    chunks = self._parallel_retrieve([f"{a} {b} 关系", f"{a} 与 {b} 的证据"])
                    self._stats["verify"] += 1
                    self._ingest(chunks)
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": f"已验证 {a} 与 {b},新增 {len(chunks)} 个片段。{self._graph.status()}"})
                else:
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": f"未知工具:{name}"})

            if halted:
                break
            self._graph.prune()

        return answer if answer is not None else self._final_answer(question)

# ================================================================== #
# 注册为可切换算法:autograph
# ================================================================== #
@register("autograph")
class AutoGraphRAG(BaseRAG):
    def run(self, question: str, history: List[Turn] | None = None) -> RAGResult:
        # 追问:并入上一轮问题
        q = question
        if history:
            q = f"{history[-1]['question']} {question}"

        model = os.getenv("FOURZ_API_MODEL", "gpt-4o-mini")

        # retriever:复用项目的 get_chunk_store(),返回纯文本列表供 AutoGraph 使用
        def _retriever(sub_query: str) -> List[str]:
            items = retrieve_chunks(sub_query, top_k=self.top_k)
            return [it["page_content"] for it in items]

        engine = _AutoGraphEngine(
            retriever=_retriever, model=model, top_k=self.top_k,
            max_iterations=4, max_sub_queries=2, max_search_actions=4,
        )
        answer = engine.query(q)

        # 用最终采纳的文档还原 chunks / sources(与其它算法返回结构一致)
        docs = list(engine._graph.docs)
        chunks = [{"page_content": d, "metadata": {}} for d in docs]
        _, sources = extract_context(chunks)  # docs 无 metadata.source,则 sources 为空

        return RAGResult(
            answer=answer, sources=sources, chunks=chunks, algorithm=self.name
        )
