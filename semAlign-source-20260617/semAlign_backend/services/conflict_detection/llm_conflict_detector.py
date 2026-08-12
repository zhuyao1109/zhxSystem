"""
大模型冲突检测器 (Pro最终版) - 串行模式 + Top-K保底策略
确保即使数学相似度低，也能强制抓取候选对给大模型分析
"""

import os
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ 警告: 未检测到 openai 库")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("⚠️ 警告: 未检测到 scikit-learn 库")

class LLMConflictDetector:
    
    """类：LLMConflictDetector。"""
    def __init__(self, api_key: str = None, base_url: str = None):
        """函数内部辅助：init  。"""
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or "https://api.deepseek.com/v1"
        self.client = None
        
        if HAS_OPENAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            print("✅ DeepSeek API 客户端就绪")
        else:
            print("⚠️ 未提供API密钥或缺少库")

    def detect_conflicts(self, clauses_a: List[Dict], clauses_b: List[Dict], 
                        metadata_a: Dict, metadata_b: Dict) -> List[Dict]:
        """函数：detect conflicts。"""
        if not self.client:
            print("❌ 大模型客户端未初始化")
            return []
        
        print(f"🤖 开始智能分析... A:{len(clauses_a)}条 vs B:{len(clauses_b)}条")
        
        # 1. 预筛选 (包含保底机制)
        candidate_pairs = self._find_candidate_pairs(clauses_a, clauses_b)
        print(f"🔍 筛选出 {len(candidate_pairs)} 对候选条款送入大模型...")
        
        if not candidate_pairs:
            print("⚠️ 彻底未发现相关条款，跳过检测")
            return []

        # 2. 批量检测 (串行)
        return self._process_batches_sync(candidate_pairs, metadata_a, metadata_b)

    @staticmethod
    def _valid_text_indices(texts: List[str]) -> List[int]:
        """返回非空文本的索引。"""
        return [i for i, t in enumerate(texts) if len(t.strip()) > 0]

    def _compute_tfidf_similarity(
        self,
        texts_a: List[str],
        texts_b: List[str],
        valid_indices_a: List[int],
        valid_indices_b: List[int],
    ) -> np.ndarray:
        """使用字符级 TF-IDF 计算相似度矩阵。"""
        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(1, 2), min_df=1)
        corpus = [texts_a[i] for i in valid_indices_a] + [texts_b[i] for i in valid_indices_b]
        vectorizer.fit(corpus)
        tfidf_a = vectorizer.transform([texts_a[i] for i in valid_indices_a])
        tfidf_b = vectorizer.transform([texts_b[i] for i in valid_indices_b])
        return cosine_similarity(tfidf_a, tfidf_b)

    def _make_candidate_pair(
        self,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        valid_indices_a: List[int],
        valid_indices_b: List[int],
        row: int,
        col: int,
        similarity_matrix: np.ndarray,
    ) -> Dict:
        """根据矩阵坐标构建候选对。"""
        return {
            "clause_a": clauses_a[valid_indices_a[row]],
            "clause_b": clauses_b[valid_indices_b[col]],
            "score": float(similarity_matrix[row, col]),
        }

    def _collect_high_similarity_pairs(
        self,
        similarity_matrix: np.ndarray,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        valid_indices_a: List[int],
        valid_indices_b: List[int],
    ) -> List[Dict]:
        """策略 A: 优先选高相似度的候选对。"""
        pairs = []
        rows, cols = np.where(similarity_matrix > 0.1)
        for row, col in zip(rows, cols):
            pairs.append(
                self._make_candidate_pair(
                    clauses_a, clauses_b, valid_indices_a, valid_indices_b, row, col, similarity_matrix
                )
            )
        return pairs

    def _pair_already_exists(self, pairs: List[Dict], clause_a: Dict, clause_b: Dict) -> bool:
        """检查候选对是否已存在。"""
        return any(
            p['clause_a']['id'] == clause_a['id'] and p['clause_b']['id'] == clause_b['id']
            for p in pairs
        )

    def _collect_top_k_backup_pairs(
        self,
        pairs: List[Dict],
        similarity_matrix: np.ndarray,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        valid_indices_a: List[int],
        valid_indices_b: List[int],
        top_k: int = 30,
    ) -> None:
        """策略 B: Top-K 保底召回。"""
        print("   ℹ️ 高置信度匹配较少，启用 Top-K 暴力召回...")
        flat_indices = np.argsort(similarity_matrix.ravel())[::-1][:top_k]
        for idx in flat_indices:
            row, col = np.unravel_index(idx, similarity_matrix.shape)
            if similarity_matrix[row, col] <= 0:
                continue
            clause_a = clauses_a[valid_indices_a[row]]
            clause_b = clauses_b[valid_indices_b[col]]
            if self._pair_already_exists(pairs, clause_a, clause_b):
                continue
            pairs.append(
                self._make_candidate_pair(
                    clauses_a, clauses_b, valid_indices_a, valid_indices_b, row, col, similarity_matrix
                )
            )

    def _dedupe_sort_limit_pairs(self, pairs: List[Dict], limit: int = 30) -> List[Dict]:
        """去重、排序并限制候选对数量。"""
        unique_pairs = []
        seen = set()
        for pair in pairs:
            key = (pair['clause_a']['id'], pair['clause_b']['id'])
            if key in seen:
                continue
            seen.add(key)
            unique_pairs.append(pair)
        unique_pairs.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique_pairs[:limit]

    def _find_sklearn_candidate_pairs(
        self,
        clauses_a: List[Dict],
        clauses_b: List[Dict],
        texts_a: List[str],
        texts_b: List[str],
        valid_indices_a: List[int],
        valid_indices_b: List[int],
    ) -> List[Dict]:
        """基于 sklearn 的候选对召回。"""
        try:
            similarity_matrix = self._compute_tfidf_similarity(
                texts_a, texts_b, valid_indices_a, valid_indices_b
            )
            pairs = self._collect_high_similarity_pairs(
                similarity_matrix, clauses_a, clauses_b, valid_indices_a, valid_indices_b
            )
            if len(pairs) < 5:
                self._collect_top_k_backup_pairs(
                    pairs, similarity_matrix, clauses_a, clauses_b, valid_indices_a, valid_indices_b
                )
            return pairs
        except (ValueError, TypeError, AttributeError) as e:
            print(f"⚠️ 算法匹配出错: {e}，切换备用")
            return self._fallback_match(clauses_a, clauses_b)

    def _find_candidate_pairs(self, clauses_a: List[Dict], clauses_b: List[Dict]) -> List[Dict]:
        """
        找出候选条款对
        【核心升级】：增加 Top-K 保底机制，绝不返回空列表
        """
        texts_a = [c.get('text', '') for c in clauses_a]
        texts_b = [c.get('text', '') for c in clauses_b]
        valid_indices_a = self._valid_text_indices(texts_a)
        valid_indices_b = self._valid_text_indices(texts_b)

        if not valid_indices_a or not valid_indices_b:
            return []

        if HAS_SKLEARN:
            pairs = self._find_sklearn_candidate_pairs(
                clauses_a, clauses_b, texts_a, texts_b, valid_indices_a, valid_indices_b
            )
        else:
            pairs = self._fallback_match(clauses_a, clauses_b)

        return self._dedupe_sort_limit_pairs(pairs)

    def _fallback_match(self, clauses_a, clauses_b):
        """最简单的字符重叠匹配"""
        pairs = []
        for ca in clauses_a:
            for cb in clauses_b:
                s1 = set(ca.get('text', ''))
                s2 = set(cb.get('text', ''))
                overlap = len(s1 & s2)
                if overlap > 2: # 只要有3个字一样就匹配
                    pairs.append({"clause_a": ca, "clause_b": cb, "score": overlap})
        return pairs

    def _process_batches_sync(self, pairs: List[Dict], meta_a: Dict, meta_b: Dict) -> List[Dict]:
        """串行分批处理"""
        batch_size = 5
        all_conflicts = []
        total = (len(pairs) + batch_size - 1) // batch_size
        
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            print(f"   🚀 分析批次 {i//batch_size + 1}/{total} (共{len(batch)}组)...")
            try:
                res = self._analyze_batch_sync(batch, i + 1, meta_a, meta_b)
                if res:
                    print(f"      ✅ 本批次发现 {len(res)} 个冲突")
                all_conflicts.extend(res)
            except (RuntimeError, ValueError, KeyError, TypeError) as e:
                print(f"      ❌ 本批次异常: {e}")
        return all_conflicts

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_deepseek_sync(self, sys_prompt: str, user_prompt: str) -> str:
        """函数内部辅助：call deepseek sync。"""
        if not self.client: raise ValueError("No Client")
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": user_prompt}],
            max_tokens=2000,
            temperature=0.1, 
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _analyze_batch_sync(self, batch: List[Dict], start_id: int, _meta_a: Dict, _meta_b: Dict) -> List[Dict]:
        """函数内部辅助：analyze batch sync。"""
        prompt_content = []
        for i, pair in enumerate(batch):
            # 截取前 300 字，保留核心信息
            ta = pair['clause_a'].get('text', '')[:300].replace('\n', ' ')
            tb = pair['clause_b'].get('text', '')[:300].replace('\n', ' ')
            prompt_content.append(f"### 对比组 {start_id + i}\n【标准A】: {ta}\n【标准B】: {tb}\n")
        
        user_prompt = (
            f"作为数据标准专家，请分析以下 {len(batch)} 组数据项定义是否存在实质性冲突。\n"
            "重点关注：\n1. 数据长度/格式不一致 (如 n50 vs n100)\n2. 数据类型不一致 (如 字符型 vs 数字型)\n3. 必填性矛盾\n"
            "忽略：排版差异、无关的标点符号。\n\n" + "\n".join(prompt_content)
        )
        
        sys_prompt = """请输出JSON格式结果：
{ "conflicts": [ { "group_id": <组号>, "type": "类型冲突/长度冲突", "priority": "high", "description": "简述冲突内容" } ] }
无冲突则返回 { "conflicts": [] }"""
        
        json_str = self._call_deepseek_sync(sys_prompt, user_prompt)
        return self._parse_result(json_str, batch, start_id)

    def _parse_result(self, json_text: str, batch: List[Dict], start_id: int) -> List[Dict]:
        """函数内部辅助：parse result。"""
        res = []
        try:
            data = json.loads(json_text.replace("```json", "").replace("```", "").strip())
            for item in data.get("conflicts", []):
                gid = item.get("group_id")
                if gid is not None:
                    idx = gid - start_id
                    if 0 <= idx < len(batch):
                        pair = batch[idx]
                        res.append({
                            "conflict_id": f"llm_{gid}",
                            "clause_a": pair["clause_a"],
                            "clause_b": pair["clause_b"],
                            "conflict_type": item.get("type", "未知"),
                            "description": item.get("description", "检测到冲突"),
                            "priority_level": item.get("priority", "medium")
                        })
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return res