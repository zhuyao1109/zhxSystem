"""规则编排器 — 融合多条优先级规则输出最终推荐。"""

"""规则编排器 — 融合多条优先级规则输出最终推荐。"""

from typing import Dict, Any
from .priority_rules import (
    InternationalPriorityRule,
    LatestRevisionRule,
    MandatoryPriorityRule
)

class RuleOrchestrator:
    """多规则编排器，按配置启用规则并融合评估结果。"""
    def __init__(self, config: Dict[str, Any]):
        """函数内部辅助：init  。"""
        self.config = config
        self.rules = self._init_rules()
    
    def _init_rules(self):
        """根据 enabled_rules 实例化具体优先级规则。"""
        rules = {}
        
        if self.config.get("enabled_rules", {}).get("international_priority"):
            rules["international_priority"] = InternationalPriorityRule()
        
        if self.config.get("enabled_rules", {}).get("latest_revision"):
            rules["latest_revision"] = LatestRevisionRule()
        
        if self.config.get("enabled_rules", {}).get("mandatory_priority"):
            rules["mandatory_priority"] = MandatoryPriorityRule()
        
        return rules
    
    def evaluate(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """对冲突条目依次执行已启用规则并输出最终推荐。"""
        if not self.rules:
            return {
                "final_recommendation": "未启用任何规则",
                "confidence": 0.0,
                "requires_user_decision": True
            }
        
        rule_results = {}
        for rule_name, rule_instance in self.rules.items():
            result = rule_instance.evaluate(
                conflict["clause_a"],
                conflict["clause_b"]
            )
            rule_results[rule_name] = result
        
        strategy = self.config.get("strategy", "weighted_sum")
        
        if strategy == "weighted_sum":
            return self._weighted_sum_strategy(rule_results)
        elif strategy == "hierarchical":
            return self._hierarchical_strategy(rule_results)
        else:
            return self._user_choice_strategy(rule_results)
    
    def _weighted_sum_strategy(self, rule_results: Dict[str, Dict]) -> Dict[str, Any]:
        """按权重加权求和融合多规则得分。"""
        weights = self.config.get("weights", {})
        
        score_a = 0.0
        score_b = 0.0
        total_weight = 0.0
        rule_details = {}
        
        for rule_name, result in rule_results.items():
            weight = weights.get(rule_name, 1.0 / len(rule_results))
            
            if result["recommendation"] == "adopt_clause_a":
                score_a += result["confidence"] * weight
            elif result["recommendation"] == "adopt_clause_b":
                score_b += result["confidence"] * weight
            
            total_weight += weight
            rule_details[rule_name] = {
                "recommendation": result["recommendation"],
                "confidence": result["confidence"],
                "reason": result["reason"],
                "weight": weight
            }
        
        if total_weight > 0:
            score_a = score_a / total_weight
            score_b = score_b / total_weight
            
            if score_a > score_b and (score_a - score_b) > 0.1:
                return {
                    "final_recommendation": "建议采用中航信标准",
                    "confidence": score_a,
                    "rule_details": rule_details,
                    "requires_user_decision": False,
                    "decision_logic": f"权重叠加: 条款A得分{score_a:.2f} > 条款B得分{score_b:.2f}"
                }
            elif score_b > score_a and (score_b - score_a) > 0.1:
                return {
                    "final_recommendation": "建议采用国际标准",
                    "confidence": score_b,
                    "rule_details": rule_details,
                    "requires_user_decision": False,
                    "decision_logic": f"权重叠加: 条款B得分{score_b:.2f} > 条款A得分{score_a:.2f}"
                }
        
        return {
            "final_recommendation": "规则建议接近，需要人工决策",
            "confidence": max(score_a, score_b),
            "rule_details": rule_details,
            "requires_user_decision": True,
            "decision_logic": f"规则建议接近: 条款A得分{score_a:.2f}, 条款B得分{score_b:.2f}"
        }
    
    def _hierarchical_strategy(self, rule_results: Dict[str, Dict]) -> Dict[str, Any]:
        """按规则优先级层级选取最终推荐。"""
        priority_order = ["mandatory_priority", "international_priority", "latest_revision"]
        
        for rule_name in priority_order:
            if rule_name in rule_results:
                result = rule_results[rule_name]
                if result["recommendation"] != "no_recommendation":
                    rule_details = {rule_name: result}
                    
                    if result["recommendation"] == "adopt_clause_a":
                        return {
                            "final_recommendation": f"根据{rule_name}规则，建议采用中航信标准",
                            "confidence": result["confidence"],
                            "rule_details": rule_details,
                            "requires_user_decision": False,
                            "decision_logic": f"层级决策: {rule_name}规则生效"
                        }
                    elif result["recommendation"] == "adopt_clause_b":
                        return {
                            "final_recommendation": f"根据{rule_name}规则，建议采用国际标准",
                            "confidence": result["confidence"],
                            "rule_details": rule_details,
                            "requires_user_decision": False,
                            "decision_logic": f"层级决策: {rule_name}规则生效"
                        }
        
        return {
            "final_recommendation": "无明确规则建议",
            "confidence": 0.5,
            "rule_details": rule_results,
            "requires_user_decision": True,
            "decision_logic": "所有规则均无明确推荐"
        }
    
    def _user_choice_strategy(self, rule_results: Dict[str, Dict]) -> Dict[str, Any]:
        """无法自动裁决时标记需用户决策。"""
        recommendations = {"adopt_clause_a": 0, "adopt_clause_b": 0, "no_recommendation": 0}
        reasons = {"adopt_clause_a": [], "adopt_clause_b": []}
        
        for rule_name, result in rule_results.items():
            rec = result["recommendation"]
            recommendations[rec] = recommendations.get(rec, 0) + 1
            
            if rec == "adopt_clause_a":
                reasons["adopt_clause_a"].append(f"{rule_name}: {result['reason']}")
            elif rec == "adopt_clause_b":
                reasons["adopt_clause_b"].append(f"{rule_name}: {result['reason']}")
        
        return {
            "final_recommendation": "需要用户决策",
            "confidence": max(recommendations.values()) / len(rule_results),
            "rule_details": rule_results,
            "requires_user_decision": True,
            "recommendation_stats": recommendations,
            "recommendation_reasons": reasons,
            "decision_logic": f"用户选择策略: {recommendations}"
        }