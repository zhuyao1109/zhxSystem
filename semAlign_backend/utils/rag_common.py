"""
utils/rag_common.py
-------------------
RAG 的共享基础设施 + 基线算法(naive) + 算法调度总入口。

设计要点:
- 只有最基础的原始算法(naive)写在本文件里。
- 其余算法(hyde / algo3 / algo4 ...)各自单独成文件,import 本模块并 @register 注册。
- 对外统一通过 rag_dispatch(question, top_k, history, algorithm) 调用。
- 算法选择优先级:显式传参 algorithm > 环境变量 RAG_ALGORITHM > naive 兜底。
- 中文系统:所有中间步骤与最终回答均强制简体中文。
"""
import os
import logging
import importlib
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, TypedDict

from openai import OpenAI
from dotenv import load_dotenv

from utils.document_processor import get_chunk_store

logger = logging.getLogger(__name__)
load_dotenv()

Turn = Dict[str, str]          # {"question": ..., "answer": ...}

# 其余算法所在的模块名(惰性导入,触发它们向注册表登记)。
# 新增算法文件后,把模块名加到这里即可。
# 可选: naive(内置) / hyde / rqrag / autograph
_ALGO_MODULES = ["utils.hyde", "utils.rqrag", "utils.autograph"]

# ================================================================== #
# LLM 单例(与原 rag.py 完全一致)
# ================================================================== #
_llm: OpenAI | None = None

def get_llm() -> OpenAI:
    global _llm
    if _llm is None:
        _llm = OpenAI(
            api_key=os.getenv("FOURZ_API_KEY"),
            base_url=os.getenv("FOURZ_API_BASE"),
        )
        if not _llm.api_key:
            logger.warning("FOURZ_API_KEY 未设置,LLM 调用将失败")
    return _llm

# ================================================================== #
# 返回结构
# ================================================================== #
class RAGResult(TypedDict, total=False):
    answer:    str                    # 大模型生成的回答(中文)
    sources:   List[str]              # 引用来源文件名(去重)
    chunks:    List[Dict[str, Any]]   # 原始检索块 {page_content, metadata}
    algorithm: str                    # 本次使用的算法名

# ================================================================== #
# 公共:检索 & 上下文抽取 & LLM 调用
# ================================================================== #
def retrieve_chunks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """统一检索入口,返回 [{page_content, metadata}, ...]"""
    store = get_chunk_store()
    if store is None:
        logger.warning("ChunkStore 不可用，返回空检索结果")
        return []
    return store.retrieve(query, top_k=top_k)

def extract_context(chunks: List[Dict[str, Any]]) -> "tuple[str, List[str]]":
    """从检索块里抽出拼接后的上下文文本 + 去重来源列表"""
    content_list: List[str] = []
    sources: List[str] = []
    for item in chunks:
        content_list.append(item["page_content"])
        src = item.get("metadata", {}).get("source", "")
        if src and src not in sources:
            sources.append(src)
    return "\n\n".join(content_list), sources

def call_llm(prompt: str, system: str, history: List[Turn] | None = None) -> str:
    """把历史多轮 + 最终 prompt 组装成 messages 调 LLM"""
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        for turn in history:
            if turn.get("question"):
                messages.append({"role": "user", "content": turn["question"]})
            if turn.get("answer"):
                messages.append({"role": "assistant", "content": turn["answer"]})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = get_llm().chat.completions.create(
            model=os.getenv("FOURZ_API_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("LLM_TOP_P", "0.85")),
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.error("LLM 调用失败: %s", exc, exc_info=True)
        return "(AI 生成失败,请稍后重试)"

# 最终回答 system prompt —— 中文系统,强制中文作答(沿用原 rag.py 的措辞并中文化)
DEFAULT_SYSTEM = (
    "你是一个基于检索内容进行解释与展开的助手。"
    "你的回答必须主要依据提供的检索上下文,不得与其中陈述的事实相矛盾。"
    "你可以对内容进行改写并补充必要的解释,帮助用户更好地理解。"
    "如果检索上下文缺少关键信息,你可以补充合理的额外信息。"
    "无论问题以何种语言提出,都必须使用【简体中文】作答。"
)

# ================================================================== #
# 基类 + 注册表(供各算法文件复用)
# ================================================================== #
class BaseRAG(ABC):
    name: str = "base"

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    @abstractmethod
    def run(self, question: str, history: List[Turn] | None = None) -> RAGResult:
        ...

ALGORITHMS: Dict[str, type] = {}

def register(name: str) -> Callable[[type], type]:
    """算法文件用它把自己登记进注册表。用法: @register("hyde")"""
    def _wrap(cls: type) -> type:
        cls.name = name
        ALGORITHMS[name] = cls
        return cls
    return _wrap

# ================================================================== #
# 基线算法:Naive 唯一写在 common 里的算法
#   最终回答强制中文。
# ================================================================== #
@register("naive")
class NaiveRAG(BaseRAG):
    def run(self, question: str, history: List[Turn] | None = None) -> RAGResult:
        # 追问时,用「上一轮问题 + 本轮问题」做检索,召回更相关
        retrieval_query = question
        if history:
            retrieval_query = f"{history[-1]['question']} {question}"

        chunks = retrieve_chunks(retrieval_query, top_k=self.top_k)
        context, sources = extract_context(chunks)

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

# ================================================================== #
# 调度:惰性加载其余算法文件 + 分发
# ================================================================== #
_loaded = False

def _ensure_loaded() -> None:
    """首次调度时,导入各算法模块,触发它们 @register 注册。"""
    global _loaded
    if _loaded:
        return
    for mod in _ALGO_MODULES:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            logger.warning("算法模块 %s 尚不存在,跳过", mod)
        except Exception as exc:
            logger.error("加载算法模块 %s 失败: %s", mod, exc, exc_info=True)
    _loaded = True

def get_default_algorithm() -> str:
    """
    读取默认算法:实时读取环境变量 RAG_ALGORITHM,未设置则用 naive。
    实时读取 = 改 .env 并重新加载后即可切换,无需改代码。
    """
    return (os.getenv("RAG_ALGORITHM", "naive") or "naive").strip() or "naive"

def list_algorithms() -> List[str]:
    _ensure_loaded()
    return list(ALGORITHMS.keys())

def rag_dispatch(
    question: str,
    top_k: int = 5,
    history: List[Turn] | None = None,
    algorithm: str | None = None,      # None = 跟随环境变量 RAG_ALGORITHM
) -> RAGResult:
    """
    总入口:按算法名选择实现并执行。
    优先级:显式传参 algorithm > 环境变量 RAG_ALGORITHM > naive。
    未知算法回退 naive。
    """
    _ensure_loaded()

    chosen = algorithm or get_default_algorithm()      # 传参优先,否则环境变量
    if chosen not in ALGORITHMS:
        logger.warning("未知算法 '%s',回退到 naive", chosen)
        chosen = "naive"

    logger.info("本次检索使用算法: %s", chosen)
    print(f"本次检索使用算法: {chosen}")
    engine = ALGORITHMS[chosen](top_k=top_k)
    return engine.run(question, history=history)
