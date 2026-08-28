"""
utils/rag.py
------------
对外统一入口。search.py 只需 from utils.rag import rag_query，签名向后兼容。

算法选择优先级：显式传参 algorithm > 环境变量 RAG_ALGORITHM > naive。
- 不传 algorithm（默认 None）即跟随 .env 里的 RAG_ALGORITHM；未设置则走 naive，
  行为与旧版完全一致。
- 真正的调度与算法实现在 utils.rag_common 及各算法文件（hyde / rqrag / autograph）中。

切换算法（推荐）：在 .env 中设置
    RAG_ALGORITHM=hyde        # naive(默认) / hyde / rqrag / autograph
"""
import os
import logging
from typing import Dict, List

from dotenv import load_dotenv

from utils.rag_common import RAGResult, rag_dispatch, list_algorithms

logger = logging.getLogger(__name__)
logger.info("加载 .env 文件: %s", os.getenv("DOTENV_PATH"))
load_dotenv()


def rag_query(
    question: str,
    top_k: int = 5,
    history: List[Dict[str, str]] | None = None,
    algorithm: str | None = None,
) -> RAGResult:
    """
    检索 + 生成，一步到位。

    Args:
        question  : 用户问题（追问时就是追问本身，不用手动拼接）
        top_k     : 检索块数量
        history   : 之前的问答轮次 [{"question": ..., "answer": ...}, ...]
        algorithm : 算法名；None 表示跟随环境变量 RAG_ALGORITHM。
                    可选：naive(默认) / hyde / rqrag / autograph

    Returns:
        RAGResult(answer, sources, chunks, algorithm)
    """
    algo = (algorithm or "").strip() or None
    return rag_dispatch(question, top_k=top_k, history=history, algorithm=algo)


def available_algorithms() -> List[str]:
    """供前端或运维查询可选算法。"""
    return list_algorithms()


__all__ = ["rag_query", "available_algorithms", "RAGResult"]
