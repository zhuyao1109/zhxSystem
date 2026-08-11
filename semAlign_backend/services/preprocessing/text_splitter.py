import re
from typing import List, Dict, Any

class TextSplitter:
    def __init__(self, min_length: int = 20, max_length: int = 500):
        self.min_length = min_length
        self.max_length = max_length
    
    def split_into_clauses(self, text: str, section_title: str = "") -> List[Dict[str, Any]]:
        """将文本分割为条款"""
        clauses = []
        
        # 先按句子分割
        sentences = self._split_sentences(text)
        
        current_clause = ""
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # 检查是否应该开始新条款
            if self._should_start_new_clause(sentence, current_clause):
                if current_clause and len(current_clause.strip()) >= self.min_length:
                    clauses.append({
                        "text": current_clause.strip(),
                        "section": section_title
                    })
                current_clause = sentence
            else:
                current_clause += " " + sentence
        
        # 添加最后一个条款
        if current_clause and len(current_clause.strip()) >= self.min_length:
            clauses.append({
                "text": current_clause.strip(),
                "section": section_title
            })
        
        return clauses
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 中文句子结束符
        sentence_endings = ['。', '！', '？', '；', '\n']
        result = []
        current = ""
        
        for char in text:
            current += char
            if char in sentence_endings:
                result.append(current.strip())
                current = ""
        
        if current.strip():
            result.append(current.strip())
        
        return result
    
    def _should_start_new_clause(self, sentence: str, current_clause: str) -> bool:
        """判断是否应该开始新条款"""
        # 如果当前条款太长，开始新的
        if len(current_clause) > self.max_length:
            return True
        
        # 如果句子以条款编号开头
        if re.match(r'^((\d+[\.、])|([一二三四五六七八九十]+[、.]))', sentence.strip()):
            return True
        
        # 如果句子以列表符号开头
        if re.match(r'^[-•*]', sentence.strip()):
            return True
        
        # 如果句子包含特定的条款开始关键词
        clause_starters = ["条款", "第", "规定", "要求", "标准", "应当", "必须"]
        if any(starter in sentence[:10] for starter in clause_starters):
            return len(current_clause) > 50
        
        return False