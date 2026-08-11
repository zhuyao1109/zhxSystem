"""工作台相关模型"""

from typing import List, Any, Optional
from pydantic import BaseModel, Field


class MetricData(BaseModel):
    """
    指标数据模型 - 展示统计数字和环比增长率
    
    核心字段：title, value, unit, trend
    """
    
    title: str = Field(..., description="指标标题")
    value: int = Field(..., description="指标值")
    unit: str = Field(..., description="单位")
    trend: Optional[float] = Field(None, description="环比增长率（百分比）")


class ChartData(BaseModel):
    """
    图表数据模型 - 饼图数据点
    
    用于分类分布、生命周期等饼图
    """
    
    name: str = Field(..., description="数据点名称")
    value: int = Field(..., description="数据点值")


class EfficiencyData(BaseModel):
    """
    效率数据模型 - 标准流程效率指标
    
    包含月度评审和发布周期数据
    """
    
    name: str = Field(..., description="横轴刻度（月份）")
    review: float = Field(..., description="评审周期（天）")
    publish: float = Field(..., description="发布周期（天）")


class EfficiencyKPIs(BaseModel):
    """
    效率KPI模型 - 标准流程效率关键指标
    
    包含平均周期和环比变化数据
    """
    
    avg_review_days: float = Field(..., description="平均评审周期（天）")
    avg_publish_days: float = Field(..., description="平均发布周期（天）")
    review_mom_delta: float = Field(..., description="评审周期较上月变化（天）")
    publish_mom_delta: float = Field(..., description="发布周期较上月变化（天）")


class StageDistributionData(BaseModel):
    """
    阶段分布数据模型 - 生命周期阶段分布
    
    展示当前和上月数量对比
    """
    
    name: str = Field(..., description="阶段名称")
    current: int = Field(..., description="当前数量")
    last: int = Field(..., description="上月数量")


class DynamicData(BaseModel):
    """
    动态数据模型 - 标准操作动态信息
    
    包含新增、修订等操作记录
    """
    
    id: str = Field(..., description="动态ID")
    type: str = Field(..., description="类型（import/update）")
    description: str = Field(..., description="描述")
    time: str = Field(..., description="时间")


class DashboardResponse(BaseModel):
    """
    工作台响应模型 - 完整的仪表板数据
    
    包含关键指标、图表数据和动态信息
    """
    
    metrics: List[MetricData] = Field(default_factory=list, description="关键指标列表")
    charts: dict = Field(default_factory=dict, description="图表数据字典")
    dynamics: List[DynamicData] = Field(default_factory=list, description="动态信息列表")