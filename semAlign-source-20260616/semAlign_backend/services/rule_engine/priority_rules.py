"""标准对齐优先级规则集。

实现国际标准优先、最新修订优先、强制性标准优先等可配置策略，
供 RuleOrchestrator 在冲突裁决阶段调用。
"""

from typing import Dict, Any
import re
from datetime import datetime
from abc import ABC, abstractmethod

class BaseRule(ABC):
    """优先级规则抽象基类，定义条款对与元数据评估接口。"""

    @abstractmethod
    def evaluate(self, clause_a: Dict, clause_b: Dict) -> Dict[str, Any]:
        """对一对冲突条款执行本规则并返回推荐与置信度。"""
        pass
    
    def _get_standard_type(self, metadata: Dict) -> str:
        """根据 publisher 字段判断国际/国内/未知类型。"""
        org = metadata.get("publisher", "").lower()
        
        international_keywords = ["iata", "icao", "iso", "国际", "international"]
        domestic_keywords = ["中航信", "cata", "民航局", "中国"]
        
        for keyword in international_keywords:
            if keyword in org:
                return "international"
        
        for keyword in domestic_keywords:
            if keyword in org:
                return "domestic"
        
        return "unknown"
    
    def _extract_date(self, metadata: Dict):
        """从元数据中解析发布日期，支持多种格式。"""
        date_str = metadata.get("publish_date")
        
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        date_formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
            "%Y年%m月%d日", "%Y-%m", "%Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        
        return None
    
    def _is_mandatory(self, clause_text: str) -> bool:
        """根据 shall/must/必须 等关键词识别强制性表述。"""
        mandatory_keywords = ["必须", "应", "shall", "must", "required"]
        return any(keyword in clause_text for keyword in mandatory_keywords)
    
    def _get_mandatory_level(self, clause_text: str) -> int:
        """函数内部辅助：get mandatory level。"""
        high_keywords = ["必须", "应", "shall", "must", "required"]
        medium_keywords = ["应该", "宜", "should", "recommended"]
        low_keywords = ["可以", "可", "may", "optional"]
        
        for keyword in high_keywords:
            if keyword in clause_text:
                return 3
        
        for keyword in medium_keywords:
            if keyword in clause_text:
                return 2
        
        for keyword in low_keywords:
            if keyword in clause_text:
                return 1
        
        return 0

class InternationalPriorityRule(BaseRule):
    """国际标准优先于国内标准的判定规则。"""
    def evaluate(self, clause_a: Dict, clause_b: Dict) -> Dict[str, Any]:
        """对一对冲突条款执行本规则并返回推荐与置信度。"""
        type_a = self._get_standard_type(clause_a.get("document_metadata", {}))
        type_b = self._get_standard_type(clause_b.get("document_metadata", {}))
        
        if type_a == "international" and type_b != "international":
            return {
                "recommendation": "adopt_clause_a",
                "confidence": 0.9,
                "reason": "条款A来自国际标准"
            }
        elif type_b == "international" and type_a != "international":
            return {
                "recommendation": "adopt_clause_b",
                "confidence": 0.9,
                "reason": "条款B来自国际标准"
            }
        elif type_a == "international" and type_b == "international":
            return {
                "recommendation": "no_recommendation",
                "confidence": 0.5,
                "reason": "两个条款都来自国际标准"
            }
        else:
            return {
                "recommendation": "no_recommendation",
                "confidence": 0.3,
                "reason": "都不是国际标准"
            }

class LatestRevisionRule(BaseRule):
    """较新发布日期优先的判定规则。"""
    def evaluate(self, clause_a: Dict, clause_b: Dict) -> Dict[str, Any]:
        """对一对冲突条款执行本规则并返回推荐与置信度。"""
        date_a = self._extract_date(clause_a.get("document_metadata", {}))
        date_b = self._extract_date(clause_b.get("document_metadata", {}))
        
        if date_a and date_b:
            if date_a > date_b:
                return {
                    "recommendation": "adopt_clause_a",
                    "confidence": 0.85,
                    "reason": f"条款A更新 ({date_a.strftime('%Y-%m-%d')})"
                }
            elif date_b > date_a:
                return {
                    "recommendation": "adopt_clause_b",
                    "confidence": 0.85,
                    "reason": f"条款B更新 ({date_b.strftime('%Y-%m-%d')})"
                }
            else:
                return {
                    "recommendation": "no_recommendation",
                    "confidence": 0.5,
                    "reason": "修订日期相同"
                }
        elif date_a and not date_b:
            return {
                "recommendation": "adopt_clause_a",
                "confidence": 0.7,
                "reason": "条款A有明确日期，条款B无日期"
            }
        elif date_b and not date_a:
            return {
                "recommendation": "adopt_clause_b",
                "confidence": 0.7,
                "reason": "条款B有明确日期，条款A无日期"
            }
        else:
            return {
                "recommendation": "no_recommendation",
                "confidence": 0.3,
                "reason": "无法确定修订日期"
            }

class MandatoryPriorityRule(BaseRule):
    """强制性条款优先于推荐性条款的判定规则。"""
    def evaluate(self, clause_a: Dict, clause_b: Dict) -> Dict[str, Any]:
        """对一对冲突条款执行本规则并返回推荐与置信度。"""
        text_a = clause_a.get("text", "")
        text_b = clause_b.get("text", "")
        
        level_a = self._get_mandatory_level(text_a)
        level_b = self._get_mandatory_level(text_b)
        
        type_a = clause_a.get("document_metadata", {}).get("standard_type", "")
        type_b = clause_b.get("document_metadata", {}).get("standard_type", "")
        
        score_a = self._calculate_score(level_a, type_a)
        score_b = self._calculate_score(level_b, type_b)
        
        if score_a > score_b:
            return {
                "recommendation": "adopt_clause_a",
                "confidence": min(0.5 + (score_a - score_b) * 0.1, 0.9),
                "reason": "条款A更具强制性"
            }
        elif score_b > score_a:
            return {
                "recommendation": "adopt_clause_b",
                "confidence": min(0.5 + (score_b - score_a) * 0.1, 0.9),
                "reason": "条款B更具强制性"
            }
        else:
            return {
                "recommendation": "no_recommendation",
                "confidence": 0.5,
                "reason": "强制性程度相当"
            }
    
    def _calculate_score(self, text_level: int, standard_type: str) -> float:
        """函数内部辅助：calculate score。"""
        score = float(text_level)
        
        type_scores = {
            "mandatory": 2.0,
            "technical": 1.0,
            "recommended": 0.5,
            "": 1.0
        }
        
        score += type_scores.get(standard_type.lower() if standard_type else "", 1.0)
        return score

def create_rule(rule_name: str):
    """函数：create rule。"""
    rules = {
        "international_priority": InternationalPriorityRule,
        "latest_revision": LatestRevisionRule,
        "mandatory_priority": MandatoryPriorityRule
    }
    
    rule_class = rules.get(rule_name)
    if rule_class:
        return rule_class()
    raise ValueError(f"未知的规则名称: {rule_name}")