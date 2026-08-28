"""
utils/rqrag.py
--------------
RQ-RAG(Refine Query RAG)算法。

三步流程:
  1) 分析并精炼查询:LLM 判断问题类型(SIMPLE / COMPLEX / AMBIGUOUS),
     并输出 1~4 个精炼后的子查询(JSON)。
  2) 多路径检索:每个子查询各自检索,合并并去重(保留顺序)。
  3) 生成回答:基于合并后的上下文,用中文作答。

复用 rag_common 的检索 / LLM 基建,不自建 FAISS、不读 CSV,
与原始网页版共用同一个 get_chunk_store()。
中文系统:中间(子查询精炼)与最终回答均强制简体中文。
"""
import json
import re
import logging
from typing import Any, Dict, List

from utils.rag_common import (
    BaseRAG, RAGResult, Turn, register,
    retrieve_chunks, extract_context, call_llm, DEFAULT_SYSTEM,
)

logger = logging.getLogger(__name__)

@register("rqrag")
class RQRAG(BaseRAG):
    # 查询分析(第一步)的 system
    ANALYZE_SYSTEM = "你是 RQ-RAG 的查询分析器,只输出严格的 JSON,不要输出多余内容。"

    # 每个子查询检索时,允许的最大子查询数(防止 LLM 拆得过多)
    MAX_SUB_QUERIES = 4

    def _analyze_query(self, question: str, history: List[Turn] | None) -> List[str]:
        """第一步:分析并精炼查询,返回子查询列表(失败则回退为 [question])。"""
        prompt = (
            "请分析下面的问题,并决定如何优化它以便技术检索。分类规则:\n"
            "1. SIMPLE:直接的问题。输出 1 个精炼后的查询。\n"
            "2. COMPLEX:多部分/多意图的问题。拆解为 2~4 个具体的子查询。\n"
            "3. AMBIGUOUS:含糊的问题。澄清概念后输出 1 个清晰的检索查询。\n\n"
            "所有子查询都必须使用【简体中文】。\n"
            "只返回如下格式的 JSON 对象,不要输出其它任何内容:\n"
            '{\n  "type": "SIMPLE/COMPLEX/AMBIGUOUS",\n  "queries": ["查询1", "查询2", ...]\n}\n\n'
            f"问题:\n{question}"
        )
        raw = call_llm(prompt, system=self.ANALYZE_SYSTEM, history=history)

        # 鲁棒性处理:去掉可能的 ```json ... ``` 包裹
        cleaned = re.sub(r"```json\s*|\s*```", "", raw or "").strip()
        try:
            data: Dict[str, Any] = json.loads(cleaned)
            queries = data.get("queries") or []
            queries = [str(q).strip() for q in queries if str(q).strip()]
            if not queries:
                raise ValueError("空的 queries")
            return queries[: self.MAX_SUB_QUERIES]
        except Exception as exc:
            logger.warning("查询分析失败,回退到简单模式: %s", exc)
            return [question]

    def _multi_retrieve(self, queries: List[str]) -> List[Dict[str, Any]]:
        """第二步:多路径检索,合并各子查询命中块,按 page_content 去重(保留顺序)。"""
        merged: List[Dict[str, Any]] = []
        seen: set = set()
        for q in queries:
            for item in retrieve_chunks(q, top_k=self.top_k):
                key = item.get("page_content", "")
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged

    def run(self, question: str, history: List[Turn] | None = None) -> RAGResult:
        # 追问时,把上一轮问题并入,便于分析器理解上下文
        analyze_input = question
        if history:
            analyze_input = f"{history[-1]['question']} {question}"

        # Step 1: 精炼出子查询
        sub_queries = self._analyze_query(analyze_input, history)

        # Step 2: 多路径检索 + 去重
        chunks = self._multi_retrieve(sub_queries)
        context, sources = extract_context(chunks)

        # Step 3: 基于合并上下文用中文生成最终回答
        answer = ""
        if context:
            prompt = (
                f"问题:{question}\n\n"
                f"检索到的上下文:\n{context}\n\n"
                "请基于以上上下文,用【简体中文】给出详细回答:"
            )
            answer = call_llm(prompt, system=DEFAULT_SYSTEM, history=history)

        return RAGResult(
            answer=answer, sources=sources, chunks=chunks, algorithm=self.name
        )
