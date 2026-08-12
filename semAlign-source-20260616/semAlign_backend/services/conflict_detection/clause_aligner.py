"""
条款对齐器 - 用于找到两个文档中相似的条款对
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from .similarity_calculator import SimilarityCalculator

class ClauseAligner:
    """条款对齐器"""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        初始化条款对齐器
        
        Args:
            similarity_threshold: 相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.similarity_calculator = SimilarityCalculator()
    
    def align_clauses(self, clauses_a: List[Dict], clauses_b: List[Dict]) -> List[Dict[str, Any]]:
        """
        对齐相似的条款
        
        Args:
            clauses_a: 文档A的条款列表
            clauses_b: 文档B的条款列表
            
        Returns:
            对齐的条款对列表
        """
        if not clauses_a or not clauses_b:
            return []
        
        print(f"🔍 开始条款对齐: {len(clauses_a)} vs {len(clauses_b)}个条款")
        
        # 提取文本
        texts_a = [c.get("text", "") for c in clauses_a]
        texts_b = [c.get("text", "") for c in clauses_b]
        
        # 计算相似度矩阵
        similarity_matrix = self.similarity_calculator.calculate_batch_similarity(texts_a, texts_b)
        
        print(f"📊 相似度矩阵计算完成: {similarity_matrix.shape}")
        
        # 找到对齐对
        aligned_pairs = self._find_aligned_pairs(
            similarity_matrix, clauses_a, clauses_b
        )
        
        print(f"✅ 找到 {len(aligned_pairs)} 个对齐的条款对")
        return aligned_pairs
    
    def _make_aligned_pair(
        self,
        clause_a: Dict,
        clause_b: Dict,
        similarity_score: float,
        pair_count: int,
    ) -> Dict:
        """构建单条对齐结果。"""
        return {
            "pair_id": f"pair_{pair_count}",
            "clause_a": clause_a,
            "clause_b": clause_b,
            "similarity_score": float(similarity_score),
            "match_type": self._get_match_type(similarity_score),
        }

    def _collect_threshold_matches(
        self,
        similarity_matrix: np.ndarray,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        used_a: set,
        used_b: set,
        aligned_pairs: List[Dict],
    ) -> None:
        """收集高于阈值的明显匹配对。"""
        for i in range(len(clauses_a)):
            for j in range(len(clauses_b)):
                score = similarity_matrix[i][j]
                if score <= self.similarity_threshold:
                    continue
                if i in used_a or j in used_b:
                    continue
                aligned_pairs.append(
                    self._make_aligned_pair(clauses_a[i], clauses_b[j], score, len(aligned_pairs))
                )
                used_a.add(i)
                used_b.add(j)

    def _collect_relaxed_matches(
        self,
        similarity_matrix: np.ndarray,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        used_a: set,
        used_b: set,
        aligned_pairs: List[Dict],
    ) -> None:
        """为未匹配条款放宽阈值寻找最佳匹配。"""
        relaxed_threshold = self.similarity_threshold * 0.8
        for i in range(len(clauses_a)):
            if i in used_a:
                continue
            best_j = np.argmax(similarity_matrix[i])
            best_score = similarity_matrix[i, best_j]
            if best_score <= relaxed_threshold or best_j in used_b:
                continue
            aligned_pairs.append(
                self._make_aligned_pair(clauses_a[i], clauses_b[best_j], best_score, len(aligned_pairs))
            )
            used_a.add(i)
            used_b.add(best_j)

    def _find_aligned_pairs(self, similarity_matrix: np.ndarray, 
                           clauses_a: List[Dict], clauses_b: List[Dict]) -> List[Dict]:
        """从相似度矩阵中找到对齐的条款对"""
        aligned_pairs = []
        used_a = set()
        used_b = set()

        self._collect_threshold_matches(
            similarity_matrix, clauses_a, clauses_b, used_a, used_b, aligned_pairs
        )

        if len(aligned_pairs) < min(len(clauses_a), len(clauses_b)) * 0.3:
            print(f"⚠️  匹配较少，尝试放宽条件...")
            self._collect_relaxed_matches(
                similarity_matrix, clauses_a, clauses_b, used_a, used_b, aligned_pairs
            )

        return aligned_pairs
    
    def _get_match_type(self, similarity_score: float) -> str:
        """根据相似度分数确定匹配类型"""
        if similarity_score >= 0.8:
            return "exact"
        elif similarity_score >= 0.6:
            return "good"
        elif similarity_score >= 0.4:
            return "partial"
        else:
            return "weak"
    
    def find_best_matches(self, query_clause: Dict, candidate_clauses: List[Dict], 
                         top_k: int = 3) -> List[Dict]:
        """
        为查询条款找到最佳匹配
        
        Args:
            query_clause: 查询条款
            candidate_clauses: 候选条款列表
            top_k: 返回top K结果
            
        Returns:
            最佳匹配列表
        """
        query_text = query_clause.get("text", "")
        candidate_texts = [c.get("text", "") for c in candidate_clauses]
        
        results = self.similarity_calculator.find_most_similar(query_text, candidate_texts, top_k)
        
        matches = []
        for idx, score in results:
            if score > self.similarity_threshold:
                matches.append({
                    "query_clause": query_clause,
                    "matched_clause": candidate_clauses[idx],
                    "similarity_score": score,
                    "rank": len(matches) + 1
                })
        
        return matches
    
    def align_by_topic(self, clauses_a: List[Dict], clauses_b: List[Dict]) -> List[Dict]:
        """
        基于主题的对齐（更智能的对齐方法）
        
        Args:
            clauses_a: 文档A的条款列表
            clauses_b: 文档B的条款列表
            
        Returns:
            对齐的条款对列表
        """
        print("🎯 基于主题的条款对齐...")
        
        # 分析每个条款的主题
        topic_clusters_a = self._cluster_by_topic(clauses_a)
        topic_clusters_b = self._cluster_by_topic(clauses_b)
        
        aligned_pairs = []
        
        # 对每个主题簇进行对齐
        for topic_a, cluster_a in topic_clusters_a.items():
            if topic_a in topic_clusters_b:
                cluster_b = topic_clusters_b[topic_a]
                
                # 在相同主题簇内进行对齐
                topic_aligned = self.align_clauses(cluster_a, cluster_b)
                
                # 重新标记pair_id
                for pair in topic_aligned:
                    pair["pair_id"] = f"{topic_a}_{len(aligned_pairs)}"
                    pair["topic"] = topic_a
                
                aligned_pairs.extend(topic_aligned)
        
        print(f"✅ 基于主题对齐完成: 找到 {len(aligned_pairs)} 个同主题条款对")
        return aligned_pairs
    
    def _cluster_by_topic(self, clauses: List[Dict]) -> Dict[str, List[Dict]]:
        """基于主题聚类条款"""
        clusters = {}
        
        for clause in clauses:
            topic_info = self.similarity_calculator.analyze_clause_topic(clause["text"])
            primary_topic = topic_info["primary_topic"]
            
            if primary_topic not in clusters:
                clusters[primary_topic] = []
            
            clause_with_topic = clause.copy()
            clause_with_topic["topic_info"] = topic_info
            clusters[primary_topic].append(clause_with_topic)
        
        return clusters