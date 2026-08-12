import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any

class ConflictVisualizer:
    """类：ConflictVisualizer。"""
    def create_priority_chart(self, conflicts: List[Dict]) -> go.Figure:
        """创建优先级分布图表"""
        priority_counts = {"高": 0, "中": 0, "低": 0}
        for conflict in conflicts:
            priority = conflict.get("priority_level", "medium")
            if priority == "high":
                priority_counts["高"] += 1
            elif priority == "medium":
                priority_counts["中"] += 1
            else:
                priority_counts["低"] += 1
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(priority_counts.keys()),
                y=list(priority_counts.values()),
                marker_color=['red', 'orange', 'green']
            )
        ])
        
        fig.update_layout(
            title="冲突优先级分布",
            xaxis_title="优先级",
            yaxis_title="数量"
        )
        
        return fig
    
    def create_type_chart(self, conflicts: List[Dict]) -> go.Figure:
        """创建冲突类型分布图表"""
        type_mapping = {
            "numerical": "数值冲突",
            "terminology": "术语冲突",
            "logical": "逻辑冲突",
            "content": "内容差异"
        }
        
        type_counts = {}
        for conflict in conflicts:
            conflict_type = conflict.get("conflict_type", "unknown")
            type_name = type_mapping.get(conflict_type, conflict_type)
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        if not type_counts:
            type_counts = {"无冲突": 1}
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(type_counts.keys()),
                values=list(type_counts.values())
            )
        ])
        
        fig.update_layout(
            title="冲突类型分布"
        )
        
        return fig
    
    def create_similarity_histogram(self, conflicts: List[Dict]) -> go.Figure:
        """创建相似度直方图"""
        if not conflicts:
            return self._create_empty_chart("无冲突数据")
        
        similarity_scores = [c.get("similarity_score", 0) for c in conflicts]
        
        fig = go.Figure(data=[
            go.Histogram(
                x=similarity_scores,
                nbinsx=20,
                marker_color='blue',
                opacity=0.7
            )
        ])
        
        fig.update_layout(
            title="相似度分布",
            xaxis_title="相似度",
            yaxis_title="数量"
        )
        
        return fig
    
    def create_conflict_table(self, conflicts: List[Dict]) -> pd.DataFrame:
        """创建冲突表格"""
        data = []
        for conflict in conflicts:
            data.append({
                "ID": conflict.get("conflict_id", ""),
                "类型": conflict.get("conflict_type", ""),
                "优先级": conflict.get("priority_level", ""),
                "描述": conflict.get("description", "")[:50],
                "相似度": f"{conflict.get('similarity_score', 0):.2%}",
                "置信度": f"{conflict.get('detection_confidence', 0):.2%}"
            })
        
        return pd.DataFrame(data)
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """创建空图表"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False}
        )
        return fig