"""
utils/hyde.py
-------------
HyDE(Hypothetical Document Embeddings)算法。

思路:
  1) 先让 LLM 针对问题写一段"假设答案(中文)";
  2) 用「原问题 + 假设文档」去检索,召回更贴近答案分布的片段;
  3) 再基于真实检索到的上下文,用中文生成最终回答。

复用 rag_common 的检索 / LLM 基建,不自建 FAISS、不读 CSV,
与原始网页版共用同一个 get_chunk_store()。
中文系统:中间"假设文档"与最终回答均强制简体中文。
"""
from typing import List

from utils.rag_common import (
    BaseRAG, RAGResult, Turn, register,
    retrieve_chunks, extract_context, call_llm, DEFAULT_SYSTEM,
)

@register("hyde")
class HyDERAG(BaseRAG):
    # 中间步骤(假设文档)的 system —— 强制中文
    HYPO_SYSTEM = "你负责针对问题撰写一段看似合理的中文答案段落,用于改进检索召回。"

    def _generate_hypothesis(self, question: str, history: List[Turn] | None) -> str:
        """HyDE 第一步:生成中文假设文档。"""
        prompt = (
            "请针对下面的问题写一段可能的答案段落,用于辅助检索。"
            "无论问题是什么语言,都必须使用【简体中文】撰写。\n"
            f"问题:{question}\n段落:"
        )
        return call_llm(prompt, system=self.HYPO_SYSTEM, history=history)

    def run(self, question: str, history: List[Turn] | None = None) -> RAGResult:
        # Step 1: 生成中文假设文档
        hypothesis = self._generate_hypothesis(question, history)
        print(f"HyDE 假设文档:\n{hypothesis}\n{'-'*40}")

        # Step 2: 用「原问题 + 假设文档」检索
        retrieval_query = f"{question}\n{hypothesis}" if hypothesis else question
        chunks = retrieve_chunks(retrieval_query, top_k=self.top_k)
        context, sources = extract_context(chunks)

        # Step 3: 基于真实上下文用中文生成最终回答
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
