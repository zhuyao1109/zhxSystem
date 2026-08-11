"""
相似度计算器 - 服务于条款对齐和冲突检测
使用轻量级模型和本地缓存，解决网络连接问题
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import jieba
import re
import math
from collections import Counter
import os

class SimilarityCalculator:
    """相似度计算器 - 增强版，解决网络连接问题"""
    
    def __init__(self, model_name: str = "", use_cache: bool = True):
        """
        初始化相似度计算器
        
        Args:
            model_name: Sentence Transformer 模型名称；为空时优先使用系统配置的本地 embedding 模型
            use_cache: 是否使用本地缓存
        """
        from core.config import settings

        self.model = None
        configured_model = str(getattr(settings, "embedding_model_dir", "") or "").strip()
        self.model_name = self._resolve_model_name(model_name or configured_model)
        self.use_cache = use_cache
        
        # 创建本地缓存目录
        if use_cache:
            cache_dir = "./models"
            os.makedirs(cache_dir, exist_ok=True)
        
        # 尝试加载模型，如果失败则使用备用方案
        self._init_model()
        
        # 民航领域关键词库（用于主题分析）
        self.aviation_keywords = {
            "准点率": ["准点", "延误", "时间", "起飞", "到达", "计划", "实际"],
            "安全标准": ["安全", "危险", "紧急", "事故", "检查", "风险"],
            "运营效率": ["运营", "效率", "成本", "管理", "优化", "绩效"],
            "服务质量": ["服务", "质量", "旅客", "乘客", "满意", "投诉"],
            "数据上报": ["数据", "报告", "统计", "记录", "上报", "采集"],
            "航班管理": ["航班", "调度", "取消", "改签", "计划", "执行"],
            "行李托运": ["行李", "托运", "重量", "尺寸", "安检", "提取"],
            "值机服务": ["值机", "登机", "柜台", "手续", "证件", "座位"]
        }
        
        # 中文停用词
        self.stopwords = set([
            '的', '了', '在', '是', '和', '与', '或', '对', '由', '从', '以', '而',
            '如果', '当', '则', '但', '且', '因此', '所以', '应当', '必须', '可以',
            '可能', '需要', '要求', '包括', '包含', '涉及', '关于', '有关', '基于'
        ])
        
        # 初始化jieba
        self._init_jieba()
        
        print(f"✅ 相似度计算器初始化完成，模型状态: {'可用' if self.model else '备用方案'}")
    
    @staticmethod
    def _resolve_model_name(preferred: str) -> str:
        """解析 embedding 模型：本地目录无效时回退到可下载的通用模型。"""
        fallback = "all-MiniLM-L6-v2"
        candidate = (preferred or "").strip()
        if not candidate:
            return fallback
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "config.json")):
            return candidate
        if not os.path.isdir(candidate):
            return candidate
        return fallback

    def _model_load_candidates(self) -> list[str]:
        """按优先级返回待尝试的模型列表。"""
        candidates = [self.model_name]
        fallback = "all-MiniLM-L6-v2"
        if fallback not in candidates:
            candidates.append(fallback)
        return candidates

    @staticmethod
    def _local_model_ready(model_name: str) -> bool:
        return os.path.isdir(model_name) and os.path.isfile(os.path.join(model_name, "config.json"))

    def _init_model(self):
        """初始化模型，提供多个备选方案"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            self.model = None
            return

        for candidate in self._model_load_candidates():
            try:
                model_kwargs: dict[str, Any] = {
                    "device": "cpu",
                    "trust_remote_code": True,
                }
                if self._local_model_ready(candidate):
                    model_kwargs["local_files_only"] = True
                self.model = SentenceTransformer(
                    candidate,
                    cache_folder="./models" if self.use_cache else None,
                    **model_kwargs,
                )
                self.model_name = candidate
                return
            except Exception:
                self.model = None
    
    def _init_jieba(self):
        """初始化jieba分词器"""
        # 添加航空领域词汇
        for keywords in self.aviation_keywords.values():
            for keyword in keywords:
                jieba.add_word(keyword)
        
        # 添加常见航空术语
        aviation_terms = [
            'ICAO', 'IATA', '航班号', '值机柜台', '登机口', '行李转盘',
            '准点率', '延误时间', '起飞时间', '到达时间', '计划时间',
            '实际时间', '安全标准', '运营效率', '服务质量'
        ]
        
        for term in aviation_terms:
            jieba.add_word(term)
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的语义相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 方案1: 使用模型计算（如果可用）
        if self.model is not None:
            try:
                embeddings = self.model.encode([text1, text2])
                similarity = np.dot(embeddings[0], embeddings[1]) / (
                    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
                )
                return float(similarity)
            except Exception as e:
                print(f"⚠️ 模型计算失败，使用备用方案: {e}")
        
        # 方案2: 使用TF-IDF余弦相似度（备用）
        return self._calculate_tfidf_similarity(text1, text2)
    
    def calculate_batch_similarity(self, texts1: List[str], texts2: List[str]) -> np.ndarray:
        """
        批量计算相似度矩阵
        
        Args:
            texts1: 文本列表1
            texts2: 文本列表2
            
        Returns:
            相似度矩阵 (len(texts1) x len(texts2))
        """
        if not texts1 or not texts2:
            return np.array([])
        
        # 方案1: 使用模型批量计算（如果可用）
        if self.model is not None:
            try:
                embeddings1 = self.model.encode(texts1)
                embeddings2 = self.model.encode(texts2)
                
                # 归一化
                embeddings1 = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
                embeddings2 = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)
                
                similarity_matrix = np.dot(embeddings1, embeddings2.T)
                return similarity_matrix
                
            except Exception as e:
                print(f"⚠️ 批量模型计算失败，使用备用方案: {e}")
        
        # 方案2: 使用TF-IDF逐对计算（备用）
        matrix = np.zeros((len(texts1), len(texts2)))
        for i, t1 in enumerate(texts1):
            for j, t2 in enumerate(texts2):
                matrix[i, j] = self._calculate_tfidf_similarity(t1, t2)
        
        return matrix
    
    def find_most_similar(self, query: str, candidates: List[str], 
                         top_k: int = 5) -> List[Tuple[int, float]]:
        """
        找到最相似的文本
        
        Args:
            query: 查询文本
            candidates: 候选文本列表
            top_k: 返回top K结果
            
        Returns:
            [(索引, 相似度), ...]
        """
        if not query or not candidates:
            return []
        
        # 方案1: 使用模型计算（如果可用）
        if self.model is not None:
            try:
                query_embedding = self.model.encode([query])
                candidate_embeddings = self.model.encode(candidates)
                
                # 归一化
                query_embedding = query_embedding / np.linalg.norm(query_embedding)
                candidate_embeddings = candidate_embeddings / np.linalg.norm(
                    candidate_embeddings, axis=1, keepdims=True
                )
                
                similarities = np.dot(query_embedding, candidate_embeddings.T)[0]
                
                # 获取top-k
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                results = [(idx, float(similarities[idx])) for idx in top_indices]
                
                return results
                
            except Exception as e:
                print(f"⚠️ 查找最相似失败，使用备用方案: {e}")
        
        # 方案2: 使用TF-IDF计算（备用）
        results = []
        for i, candidate in enumerate(candidates):
            similarity = self._calculate_tfidf_similarity(query, candidate)
            results.append((i, similarity))
        
        # 排序并取top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def analyze_clause_topic(self, text: str) -> Dict[str, Any]:
        """
        分析条款主题
        
        Args:
            text: 条款文本
            
        Returns:
            主题分析结果
        """
        # 分词
        words = [w for w in jieba.lcut(text) if w not in self.stopwords and len(w) > 1]
        
        # 匹配领域关键词
        topic_scores = {}
        for topic, keywords in self.aviation_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                topic_scores[topic] = score
        
        # 确定主要主题
        primary_topic = None
        secondary_topics = []
        
        if topic_scores:
            sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
            primary_topic = sorted_topics[0][0]
            if len(sorted_topics) > 1:
                secondary_topics = [t[0] for t in sorted_topics[1:3]]
        
        # 提取关键词
        keyword_pattern = r'(?:准点|延误|安全|服务|运营|数据|航班|行李|值机)'
        extracted_keywords = list(set(re.findall(keyword_pattern, text)))
        
        return {
            "primary_topic": primary_topic or "其他",
            "secondary_topics": secondary_topics,
            "topic_scores": topic_scores,
            "keywords": extracted_keywords,
            "word_count": len(words)
        }
    
    def _calculate_tfidf_similarity(self, text1: str, text2: str) -> float:
        """
        基于TF-IDF的余弦相似度计算（备用方案）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        # 分词
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # 合并所有词
        all_words = list(set(words1 + words2))
        
        # 计算词频
        freq1 = Counter(words1)
        freq2 = Counter(words2)
        
        # 计算TF-IDF向量
        vec1 = self._tfidf_vector(freq1, all_words, words1, words2)
        vec2 = self._tfidf_vector(freq2, all_words, words1, words2)
        
        # 计算余弦相似度
        similarity = self._cosine_similarity(vec1, vec2, all_words)
        
        return similarity
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        
        # 使用jieba分词
        words = jieba.lcut(text)
        
        # 过滤停用词和短词
        filtered = []
        for word in words:
            word = word.strip()
            if (word and 
                len(word) > 1 and 
                word not in self.stopwords and
                not word.isdigit() and
                not re.match(r'^[^\u4e00-\u9fff]+$', word)):  # 过滤纯非中文
                filtered.append(word)
        
        return filtered
    
    def _tfidf_vector(self, freq: Counter, all_words: List[str], 
                      doc1_words: List[str], doc2_words: List[str]) -> Dict[str, float]:
        """计算TF-IDF向量"""
        vector = {}
        total_terms = sum(freq.values())
        
        for word in all_words:
            # 词频 (TF)
            tf = freq.get(word, 0) / total_terms if total_terms > 0 else 0
            
            # 文档频率 (DF)
            df = 0
            if word in doc1_words:
                df += 1
            if word in doc2_words:
                df += 1
            
            # 逆文档频率 (IDF)
            idf = math.log((2 + 1) / (df + 1)) + 1  # 平滑处理
            
            vector[word] = tf * idf
        
        return vector
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float], 
                          all_words: List[str]) -> float:
        """计算余弦相似度"""
        # 构建数值向量
        v1 = [vec1.get(word, 0) for word in all_words]
        v2 = [vec2.get(word, 0) for word in all_words]
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(v1, v2))
        
        # 计算模长
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # 确保在0-1范围内
        return max(0.0, min(1.0, similarity))
    
    def _fallback_similarity(self, text1: str, text2: str) -> float:
        """备选相似度计算方法（Jaccard相似度）"""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union
    
    def _fallback_find_similar(self, query: str, candidates: List[str], 
                              top_k: int = 5) -> List[Tuple[int, float]]:
        """备选查找方法"""
        results = []
        for i, candidate in enumerate(candidates):
            similarity = self._fallback_similarity(query, candidate)
            results.append((i, similarity))
        
        # 排序并取top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# 简单的备用相似度计算器
class SimpleSimilarityCalculator:
    """简单相似度计算器 - 完全避免外部依赖"""
    
    def __init__(self):
        """初始化"""
        # 民航领域关键词库
        self.aviation_keywords = {
            "准点率": ["准点", "延误", "时间", "起飞", "到达"],
            "安全标准": ["安全", "危险", "紧急", "事故", "检查"],
            "服务质量": ["服务", "质量", "旅客", "乘客", "满意"],
            "数据上报": ["数据", "报告", "统计", "记录", "上报"],
            "航班管理": ["航班", "调度", "取消", "改签", "计划"]
        }
        
        # 初始化jieba
        try:
            import jieba
            self.jieba = jieba
        except ImportError:
            self.jieba = None
            print("⚠️ jieba未安装，使用简单分词")
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """计算相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 使用Jaccard相似度
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)
        
        if not words1 or not words2:
            return 0.0
        
        set1 = set(words1)
        set2 = set(words2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_batch_similarity(self, texts1: List[str], texts2: List[str]) -> np.ndarray:
        """批量计算相似度"""
        matrix = np.zeros((len(texts1), len(texts2)))
        for i, t1 in enumerate(texts1):
            for j, t2 in enumerate(texts2):
                matrix[i, j] = self.calculate_semantic_similarity(t1, t2)
        return matrix
    
    def find_most_similar(self, query: str, candidates: List[str], top_k: int = 5):
        """查找最相似"""
        results = []
        for i, candidate in enumerate(candidates):
            similarity = self.calculate_semantic_similarity(query, candidate)
            results.append((i, similarity))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def analyze_clause_topic(self, text: str) -> Dict[str, Any]:
        """分析主题"""
        topic_scores = {}
        for topic, keywords in self.aviation_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                topic_scores[topic] = score
        
        primary_topic = max(topic_scores, key=topic_scores.get) if topic_scores else "其他"
        
        return {
            "primary_topic": primary_topic,
            "topic_scores": topic_scores,
            "keywords": [],
            "word_count": len(text)
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        
        if self.jieba:
            # 使用jieba分词
            words = self.jieba.lcut(text)
        else:
            # 简单分词：按空格和标点分割
            words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z]+', text)
        
        # 过滤短词
        return [w for w in words if len(w) > 1]


def get_similarity_calculator(model_name: str = "all-MiniLM-L6-v2", use_cache: bool = True):
    """
    获取相似度计算器（自动选择最佳方案）
    
    Args:
        model_name: 模型名称
        use_cache: 是否使用缓存
        
    Returns:
        相似度计算器实例
    """
    try:
        calculator = SimilarityCalculator(model_name=model_name, use_cache=use_cache)
        print(f"✅ 使用增强版相似度计算器")
        return calculator
    except Exception as e:
        print(f"⚠️ 增强版计算器初始化失败，使用简单版本: {e}")
        return SimpleSimilarityCalculator()


# 测试函数
def test_similarity_calculator():
    """测试相似度计算器"""
    print("🧪 测试相似度计算器...")
    
    # 创建计算器
    calculator = get_similarity_calculator()
    
    # 测试文本
    text1 = "航班准点率应达到85%以上"
    text2 = "航班的准时率应该不低于85%"
    text3 = "安全检查必须每季度进行一次"
    
    # 测试相似度计算
    sim12 = calculator.calculate_semantic_similarity(text1, text2)
    sim13 = calculator.calculate_semantic_similarity(text1, text3)
    
    print(f"相似度 '{text1}' vs '{text2}': {sim12:.3f}")
    print(f"相似度 '{text1}' vs '{text3}': {sim13:.3f}")
    
    # 测试主题分析
    topic_info = calculator.analyze_clause_topic("航班准点率统计和报告要求")
    print(f"主题分析: {topic_info}")
    
    # 测试批量计算
    texts = [text1, text2, text3]
    matrix = calculator.calculate_batch_similarity(texts, texts)
    print(f"相似度矩阵:\n{matrix}")
    
    # 测试查找最相似
    results = calculator.find_most_similar(text1, texts, top_k=2)
    print(f"最相似结果: {results}")


if __name__ == "__main__":
    test_similarity_calculator()