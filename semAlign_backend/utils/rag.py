"""
utils/rag.py
------------
检索 + LLM 生成，封装成一个 query() 调用。
search.py 只需 from utils.rag import rag_query
"""
import os
import logging
from typing import Any, Dict, List, TypedDict

from openai import OpenAI

from utils.document_processor import get_chunk_store
from dotenv import load_dotenv
logger = logging.getLogger(__name__)
#打印.env文件位置
logger.info("加载 .env 文件: %s", os.getenv("DOTENV_PATH"))

load_dotenv()  # 从 .env 文件加载环境变量
# ------------------------------------------------------------------ #
# LLM 单例
# ------------------------------------------------------------------ #
_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """函数内部辅助：get llm。"""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            api_key=os.getenv("FOURZ_API_KEY"),
            base_url=os.getenv("FOURZ_API_BASE"),
        )
        if not _llm.api_key:
            logger.warning("FOURZ_API_KEY 未设置，LLM 调用将失败")
    return _llm


# ------------------------------------------------------------------ #
# 返回结构
# ------------------------------------------------------------------ #
class RAGResult(TypedDict):
    """类：RAGResult。"""
    answer:   str                    # 大模型生成的回答
    sources:  List[str]              # 引用来源文件名（去重）
    chunks:   List[Dict[str, Any]]   # 原始检索块 {page_content, metadata}


# ------------------------------------------------------------------ #
# 核心函数
# ------------------------------------------------------------------ #
def rag_query(question: str, top_k: int = 5) -> RAGResult:
    """
    检索 + 生成，一步到位。

    Args:
        question : 用户问题
        top_k    : 检索块数量

    Returns:
        RAGResult(answer, sources, chunks)
    """
    # 1. 向量检索
    store  = get_chunk_store()
    chunks = store.retrieve(question, top_k=top_k)

    content_list: List[str] = []
    sources:      List[str] = []

    for item in chunks:
        content_list.append(item["page_content"])
        src = item.get("metadata", {}).get("source", "")
        if src and src not in sources:
            sources.append(src)

    # 2. 构建 prompt
    context = "\n\n".join(content_list)
    prompt  = (
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Based on the context above, provide a detailed answer (in Chinese):"
    )

    # 3. 调用 LLM
    answer = ""
    if content_list:
        try:
            resp = _get_llm().chat.completions.create(
                model=os.getenv("FOURZ_API_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant that explains and elaborates answers based on retrieved content. "
                               "Your responses should primarily rely on the provided retrieval context and must not contradict the facts stated in it. "
                               "You may rephrase and provide necessary explanations to help the user better understand the content. "
                               "If the retrieval context lacks key information, you may supplement your answer with reasonable additional information."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                top_p=float(os.getenv("LLM_TOP_P", "0.85")),
            )
            answer = resp.choices[0].message.content or ""
            print("LLM 原始回答:", answer)
        except Exception as exc:
            logger.error("LLM 调用失败: %s", exc, exc_info=True)
            answer = "（AI 生成失败，请稍后重试）"

    return RAGResult(answer=answer, sources=sources, chunks=chunks)
