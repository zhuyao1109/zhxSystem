import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any
import os

class ReportGenerator:
    """类：ReportGenerator。"""
    def generate_report(self, conflicts: List[Dict], metadata_a: Dict, 
                       metadata_b: Dict, rule_config: Dict) -> Dict[str, Any]:
        """生成冲突报告"""
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "documents": {
                    "document_a": metadata_a,
                    "document_b": metadata_b
                },
                "rule_config": rule_config
            },
            "summary": self._generate_summary(conflicts),
            "conflicts": conflicts,
            "statistics": self._calculate_statistics(conflicts)
        }
        
        return report
    
    def _generate_summary(self, conflicts: List[Dict]) -> Dict[str, Any]:
        """生成摘要"""
        total_conflicts = len(conflicts)
        
        # 按优先级统计
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        for conflict in conflicts:
            priority = conflict.get("priority_level", "medium")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # 按类型统计
        type_counts = {}
        for conflict in conflicts:
            conflict_type = conflict.get("conflict_type", "unknown")
            type_counts[conflict_type] = type_counts.get(conflict_type, 0) + 1
        
        return {
            "total_conflicts": total_conflicts,
            "priority_distribution": priority_counts,
            "type_distribution": type_counts,
            "has_high_priority": priority_counts["high"] > 0
        }
    
    def _calculate_statistics(self, conflicts: List[Dict]) -> Dict[str, Any]:
        """计算统计信息"""
        if not conflicts:
            return {}
        
        similarity_scores = [c.get("similarity_score", 0) for c in conflicts]
        confidence_scores = [c.get("detection_confidence", 0) for c in conflicts]
        
        return {
            "avg_similarity": sum(similarity_scores) / len(similarity_scores),
            "avg_confidence": sum(confidence_scores) / len(confidence_scores),
            "max_similarity": max(similarity_scores),
            "min_similarity": min(similarity_scores)
        }
    
    def export_to_excel(self, report: Dict, output_path: str):
        """导出为Excel"""
        # 创建DataFrame
        conflicts_data = []
        for conflict in report.get("conflicts", []):
            conflicts_data.append({
                "冲突ID": conflict.get("conflict_id", ""),
                "冲突类型": conflict.get("conflict_type", ""),
                "优先级": conflict.get("priority_level", ""),
                "描述": conflict.get("description", ""),
                "中航信条款": conflict.get("clause_a", {}).get("text", "")[:100],
                "国际标准条款": conflict.get("clause_b", {}).get("text", "")[:100],
                "相似度": conflict.get("similarity_score", 0),
                "置信度": conflict.get("detection_confidence", 0)
            })
        
        df = pd.DataFrame(conflicts_data)
        
        # 写入Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='冲突列表', index=False)
            
            # 添加摘要工作表
            summary_data = {
                "指标": ["总冲突数", "高优先级", "中优先级", "低优先级", "平均相似度"],
                "数值": [
                    report["summary"]["total_conflicts"],
                    report["summary"]["priority_distribution"]["high"],
                    report["summary"]["priority_distribution"]["medium"],
                    report["summary"]["priority_distribution"]["low"],
                    report["statistics"]["avg_similarity"]
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='报告摘要', index=False)
    
    def export_to_markdown(self, report: Dict, output_path: str):
        """导出为Markdown"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 标准冲突检测报告\n\n")
            
            # 摘要
            f.write("## 报告摘要\n\n")
            summary = report["summary"]
            f.write(f"- **总冲突数**: {summary['total_conflicts']}\n")
            f.write(f"- **高优先级**: {summary['priority_distribution']['high']}\n")
            f.write(f"- **中优先级**: {summary['priority_distribution']['medium']}\n")
            f.write(f"- **低优先级**: {summary['priority_distribution']['low']}\n\n")
            
            # 详细冲突
            f.write("## 详细冲突列表\n\n")
            for conflict in report.get("conflicts", []):
                f.write(f"### 冲突 {conflict.get('conflict_id')}\n\n")
                f.write(f"**类型**: {conflict.get('conflict_type')}\n\n")
                f.write(f"**优先级**: {conflict.get('priority_level')}\n\n")
                f.write(f"**描述**: {conflict.get('description')}\n\n")
                f.write("**中航信条款**:\n\n")
                f.write(f"> {conflict.get('clause_a', {}).get('text', '')}\n\n")
                f.write("**国际标准条款**:\n\n")
                f.write(f"> {conflict.get('clause_b', {}).get('text', '')}\n\n")
                f.write("---\n\n")
    
    def export_to_json(self, report: Dict, output_path: str):
        """导出为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)