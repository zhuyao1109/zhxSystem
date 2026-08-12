"""工作台路由 - 处理工作台数据统计和展示"""

from datetime import datetime, timedelta
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.deps import get_db, get_current_user
from models.user import User
from models.standard import Standard
from models.alignment_task import AlignmentTask, AlignmentStatus
from models.term_conflict import ImportBatch, TermConflict
from models.conflict_dialogue import ConflictDialogue, ConflictDialogueMapping
from schemas.workbench import (
    DashboardResponse,
    MetricData,
    ChartData,
    DynamicData,
    EfficiencyData,
    EfficiencyKPIs,
    StageDistributionData
)
from schemas.base import APIResponse

router = APIRouter(prefix="/workbench", tags=["工作台"])

YEAR_MONTH_FMT = "%Y-%m"
DATETIME_DISPLAY_FMT = "%Y-%m-%d %H:%M"


# ==================== 辅助函数 ====================

def _status_to_stage(status: Optional[str]) -> str:
    """
    将标准状态映射为生命周期阶段
    
    业务逻辑：
        - 将数据库中的 status 字段映射为前端柱状图的阶段
        - 未匹配到的状态归入"已生效"，避免柱图缺列
    
    映射关系：
        - 草稿/新增 → 草案
        - 审核中 → 评审中
        - 有效 → 已生效
        - 已废止 → 已废止
        - 待废止 → 待废止
    
    Args:
        status: 标准状态
    
    Returns:
        生命周期阶段名称
    """
    if not status:
        return "已生效"
    mapping = {
        "草稿": "草案",
        "审核中": "评审中",
        "有效": "已生效",
        "新增": "草案",
        "已废止": "已废止",
        "待废止": "待废止",
    }
    return mapping.get(status, "已生效")


def _stage_bucket_counts(db: Session, as_of: Optional[datetime]) -> dict:
    """
    统计各生命周期阶段的数量
    
    业务逻辑：
        - 为「生命周期阶段分布」柱图汇总各阶段数量
        - as_of 非空时仅统计 created_at <= as_of，用于「上月数量」对比
    
    Args:
        db: 数据库会话
        as_of: 截止时间（None 表示当前）
    
    Returns:
        各阶段的数量字典
    """
    stage_labels = ["草案", "评审中", "已生效", "待废止", "已废止"]
    q = db.query(Standard.status, func.count(Standard.id)).group_by(Standard.status)
    if as_of is not None:
        q = q.filter(Standard.created_at <= as_of)
    
    buckets = {label: 0 for label in stage_labels}
    for st, cnt in q.all():
        label = _status_to_stage(st)
        buckets[label] = buckets.get(label, 0) + int(cnt)
    
    return buckets


def _build_stage_distribution(current: dict, last_month: dict) -> List[StageDistributionData]:
    """
    拼接前端「生命周期阶段分布」柱状图数据
    
    业务逻辑：
        - 生成前端 Recharts BarChart 的数据源
        - name → 横轴；current → 图例「当前数量」；last → 图例「上月数量」
    
    Args:
        current: 当前阶段统计
        last_month: 上月阶段统计
    
    Returns:
        阶段分布数据列表
    """
    stage_labels = ["草案", "评审中", "已生效", "待废止", "已废止"]
    return [
        StageDistributionData(
            name=lbl,
            current=int(current.get(lbl, 0)),
            last=int(last_month.get(lbl, 0))
        )
        for lbl in stage_labels
    ]


def _month_axis_label(y: int, m: int) -> str:
    """
    生成折线图横轴标签

    业务逻辑：
        - 统一使用"年月"格式，避免混淆

    Args:
        y: 年份
        m: 月份

    Returns:
        横轴标签
    """
    return f"{y}年{m}月"


def _iter_last_n_months(now: datetime, n: int = 6) -> List[tuple]:
    """
    从当前年月起向前数 n 个月
    
    业务逻辑：
        - 用于生成折线图的横轴时间序列
        - 时间从早到晚排序
    
    Args:
        now: 当前时间
        n: 月份数
    
    Returns:
        (年份, 月份)元组列表
    """
    y, m = now.year, now.month
    months: List[tuple] = []
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def _efficiency_series(db: Session, now: datetime) -> List[EfficiencyData]:
    """
    生成前端「标准流程效率指标」卡片内折线图的数据源
    
    业务逻辑：
        - 当前无独立流程/工单表，故为代理数据
        - 非真实 SLA
        - 新增越多，代理周期略缩短（展示相关性）
    
    Args:
        db: 数据库会话
        now: 当前时间
    
    Returns:
        效率数据列表
    """
    out: List[EfficiencyData] = []
    for y, m in _iter_last_n_months(now, 6):
        ym = f"{y:04d}-{m:02d}"
        raw = (
            db.query(func.count(Standard.id))
            .filter(func.strftime(YEAR_MONTH_FMT, Standard.created_at) == ym)
            .scalar()
        )
        cnt = int(raw or 0)
        # 新增越多，代理周期略缩短（公式可调，仅用于展示相关性）
        review = round(18.0 / (1.0 + cnt * 0.08) + 3.0, 1)
        publish = round(22.0 / (1.0 + cnt * 0.06) + 5.0, 1)
        out.append(
            EfficiencyData(
                name=_month_axis_label(y, m),
                review=review,
                publish=publish
            )
        )
    return out


def _lifecycle_by_status(db: Session) -> List[ChartData]:
    """
    前端左侧饼图「标准生命周期分布」数据
    
    业务逻辑：
        - 按状态统计标准数量
        - 未标注的状态显示为"未标注"
    
    Args:
        db: 数据库会话
    
    Returns:
        生命周期分布数据列表
    """
    rows = db.query(Standard.status, func.count(Standard.id)).group_by(Standard.status).all()
    return [ChartData(name=(s or "未标注"), value=int(c)) for s, c in rows]


def _recent_dynamics(db: Session, limit: int = 15) -> List[DynamicData]:
    """
    前端「标准动态」卡片列表数据

    业务逻辑：
        - 按更新时间倒序获取最近的标准
        - 根据 source_file 判断类型（有文件为 import，否则为 update）
        - 格式化时间显示，区分创建时间和更新时间

    Args:
        db: 数据库会话
        limit: 返回数量

    Returns:
        动态数据列表
    """
    items: List[tuple[datetime, DynamicData]] = []

    order_col = func.coalesce(Standard.updated_at, Standard.created_at)
    standards = db.query(Standard).order_by(order_col.desc()).limit(limit).all()
    for s in standards:
        dt = s.updated_at or s.created_at
        if dt is None:
            continue
        kind = "import" if (s.source_file or "") else "update"

        # 区分创建时间和更新时间
        if s.updated_at and s.created_at and s.updated_at != s.created_at:
            time_str = f"更新于 {s.updated_at.strftime(DATETIME_DISPLAY_FMT)}"
        else:
            time_str = f"创建于 {(s.created_at or dt).strftime(DATETIME_DISPLAY_FMT)}"

        items.append(
            (
                dt,
                DynamicData(
                    id=f"std-{s.id}",
                    type=kind,
                    description=f"{s.standard_no} · {s.name}",
                    time=time_str,
                ),
            )
        )

    # 移除术语冲突批次和问答对的动态信息，只保留标准文档相关的动态
    # 如果需要查看这些信息，应该在专门的页面中展示

    items.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in items[:limit]]


def _distinct_standard_no_count_from_term_conflicts(db: Session) -> int:
    rows = db.query(TermConflict.standard_no_1, TermConflict.standard_no_2).all()
    nos = set()
    for a, b in rows:
        if a:
            nos.add(a.strip())
        if b:
            nos.add(b.strip())
    return len(nos)


def _monthly_ingest_count(db: Session, ym: str) -> int:
    standards_cnt = (
        db.query(func.count(Standard.id))
        .filter(func.strftime(YEAR_MONTH_FMT, Standard.created_at) == ym)
        .scalar()
        or 0
    )
    term_cnt = (
        db.query(func.count(TermConflict.id))
        .filter(func.strftime(YEAR_MONTH_FMT, TermConflict.created_at) == ym)
        .scalar()
        or 0
    )
    dialogue_cnt = (
        db.query(func.count(ConflictDialogue.id))
        .filter(func.strftime(YEAR_MONTH_FMT, ConflictDialogue.created_at) == ym)
        .scalar()
        or 0
    )
    return int(standards_cnt) + int(term_cnt) + int(dialogue_cnt)


def _conflict_stage_bucket_counts(db: Session, as_of: Optional[datetime]) -> dict:
    group_q = db.query(func.count(func.distinct(ConflictDialogue.original_conflict_id)))
    mapped_q = db.query(func.count(func.distinct(ConflictDialogueMapping.original_conflict_id)))
    if as_of is not None:
        group_q = group_q.filter(ConflictDialogue.created_at <= as_of)
        mapped_q = mapped_q.filter(ConflictDialogueMapping.created_at <= as_of)

    total_groups = int(group_q.scalar() or 0)
    mapped_groups = int(mapped_q.scalar() or 0)
    pending = max(total_groups - mapped_groups, 0)
    return {
        "草案": 0,
        "评审中": pending,
        "已生效": mapped_groups,
        "待废止": 0,
        "已废止": 0,
    }


def _compute_month_over_month_trend(current: int, baseline: int) -> float:
    if baseline > 0:
        return round((current / baseline - 1.0) * 100.0, 1)
    if current > 0:
        return 100.0
    return 0.0


def _prev_month_start(now: datetime) -> datetime:
    if now.month == 1:
        return datetime(now.year - 1, 12, 1)
    return datetime(now.year, now.month - 1, 1)


def _build_dashboard_metrics(db: Session, now: datetime) -> List[MetricData]:
    first_day_of_month = datetime(now.year, now.month, 1)
    total_standards = int(db.query(func.count(Standard.id)).scalar() or 0)

    ym_now = f"{now.year:04d}-{now.month:02d}"
    monthly_added = int(
        db.query(func.count(Standard.id))
        .filter(func.strftime(YEAR_MONTH_FMT, Standard.created_at) == ym_now)
        .scalar() or 0
    )

    pending_alignments = int(
        db.query(func.count(AlignmentTask.id))
        .filter(AlignmentTask.status.in_([AlignmentStatus.PENDING.value, "processing"]))
        .scalar() or 0
    )

    prev_month_start = _prev_month_start(now)
    ym_prev = f"{prev_month_start.year:04d}-{prev_month_start.month:02d}"
    last_month_added = int(
        db.query(func.count(Standard.id))
        .filter(func.strftime(YEAR_MONTH_FMT, Standard.created_at) == ym_prev)
        .scalar() or 0
    )
    trend_new = _compute_month_over_month_trend(monthly_added, last_month_added)

    standards_before_month = int(
        db.query(func.count(Standard.id))
        .filter(Standard.created_at < first_day_of_month)
        .scalar() or 0
    )
    trend_total = _compute_month_over_month_trend(total_standards, standards_before_month)

    return [
        MetricData(title="标准文档总数", value=total_standards, unit="个", trend=trend_total),
        MetricData(title="本月新增文档", value=monthly_added, unit="个", trend=trend_new),
        MetricData(title="待处理对齐任务", value=pending_alignments, unit="个", trend=None),
    ]


def _build_category_charts(db: Session, total_standards: int) -> List[ChartData]:
    categories = (
        db.query(Standard.category, func.count(Standard.id))
        .group_by(Standard.category)
        .all()
    )
    if categories and total_standards >= 20:
        return [
            ChartData(name=(cat or "未分类"), value=int(count)) for cat, count in categories
        ]

    conflict_categories = (
        db.query(TermConflict.conflict_type, func.count(TermConflict.id))
        .group_by(TermConflict.conflict_type)
        .order_by(func.count(TermConflict.id).desc())
        .limit(8)
        .all()
    )
    return [
        ChartData(name=(cat or "未分类"), value=int(count))
        for cat, count in conflict_categories
    ]


def _build_lifecycle_charts(db: Session, total_standards: int) -> List[ChartData]:
    lifecycle_charts = _lifecycle_by_status(db)
    if lifecycle_charts and total_standards > 10:
        return lifecycle_charts
    conflict_stage = _conflict_stage_bucket_counts(db, None)
    return [
        ChartData(name=key, value=int(value))
        for key, value in conflict_stage.items()
        if int(value) > 0
    ]


def _build_dashboard_efficiency_series(db: Session, now: datetime) -> List[EfficiencyData]:
    eff_series: List[EfficiencyData] = []
    for y, m in _iter_last_n_months(now, 6):
        ym = f"{y:04d}-{m:02d}"
        cnt = int(
            db.query(func.count(Standard.id))
            .filter(func.strftime(YEAR_MONTH_FMT, Standard.created_at) == ym)
            .scalar() or 0
        )
        review = round(18.0 / (1.0 + cnt * 0.05) + 3.0, 1)
        publish = round(22.0 / (1.0 + cnt * 0.04) + 5.0, 1)
        eff_series.append(
            EfficiencyData(
                name=_month_axis_label(y, m),
                review=review,
                publish=publish,
            )
        )
    return eff_series


def _build_efficiency_kpis(eff_series: List[EfficiencyData]) -> EfficiencyKPIs:
    if len(eff_series) >= 2:
        avg_review = round(sum(e.review for e in eff_series) / len(eff_series), 1)
        avg_publish = round(sum(e.publish for e in eff_series) / len(eff_series), 1)
        review_mom = round(eff_series[-1].review - eff_series[-2].review, 1)
        publish_mom = round(eff_series[-1].publish - eff_series[-2].publish, 1)
    else:
        avg_review = avg_publish = review_mom = publish_mom = 0.0
    return EfficiencyKPIs(
        avg_review_days=avg_review,
        avg_publish_days=avg_publish,
        review_mom_delta=review_mom,
        publish_mom_delta=publish_mom,
    )


def _build_stage_distribution_charts(
    db: Session,
    now: datetime,
    total_standards: int,
) -> List[StageDistributionData]:
    first_day_of_month = datetime(now.year, now.month, 1)
    end_last_month = first_day_of_month - timedelta(seconds=1)
    current_stage = _stage_bucket_counts(db, None)
    last_stage = _stage_bucket_counts(db, end_last_month)
    if sum(current_stage.values()) == 0 or total_standards <= 10:
        current_stage = _conflict_stage_bucket_counts(db, None)
        last_stage = _conflict_stage_bucket_counts(db, end_last_month)
    return _build_stage_distribution(current_stage, last_stage)


# ==================== 路由接口 ====================

@router.get("/dashboard", response_model=APIResponse[DashboardResponse])
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取工作台数据接口
    
    业务逻辑：
        1. 统计标准总数和环比增长率
        2. 统计本月新增标准和环比增长率
        3. 统计待处理对齐任务
        4. 统计标准分类分布（饼图）
        5. 统计标准生命周期分布（饼图）
        6. 统计标准流程效率（折线图 + KPI）
        7. 统计生命周期阶段分布（柱状图）
        8. 获取最近的标准动态
    
    返回数据：
        - metrics: 关键指标（3个）
            - 标准总数（带环比）
            - 本月新增（带环比）
            - 待处理对齐（无环比）
        - charts: 图表数据（7种）
            - distribution: 分类分布饼图
            - category: 分类分布柱状图（与distribution相同）
            - lifecycle: 生命周期饼图
            - efficiency: 效率折线图
            - efficiency_kpis: 效率KPI
            - stage_distribution: 阶段分布柱状图
            - trend: 预留字段
            - comparison: 预留字段
        - dynamics: 动态信息（最近15条）
    
    前端使用示例：
        const response = await api.getDashboard();
        const { metrics, charts, dynamics } = response.data;
        
        // 渲染指标卡片
        metrics.forEach(metric => {
            console.log(metric.title, metric.value, metric.trend);
        });
        
        // 渲染图表
        console.log(charts.lifecycle);           // 生命周期饼图
        console.log(charts.efficiency);          // 效率折线图
        console.log(charts.efficiency_kpis);     // 效率KPI
        console.log(charts.stage_distribution);  // 阶段分布柱状图
        
        // 渲染动态列表
        dynamics.forEach(dynamic => {
            console.log(dynamic.type, dynamic.description);
        });
    
    注意事项：
        - 所有指标数据实时计算
        - 图表数据按分类、状态等聚合
        - 动态信息按时间倒序
        - 效率数据为代理数据，非真实 SLA
    
    Args:
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        APIResponse[DashboardResponse]: 工作台数据响应
    """
    now = datetime.now()
    total_standards = int(db.query(func.count(Standard.id)).scalar() or 0)

    metrics = _build_dashboard_metrics(db, now)
    category_charts = _build_category_charts(db, total_standards)
    lifecycle_charts = _build_lifecycle_charts(db, total_standards)
    eff_series = _build_dashboard_efficiency_series(db, now)
    efficiency_kpis = _build_efficiency_kpis(eff_series)
    stage_distribution = _build_stage_distribution_charts(db, now, total_standards)

    charts = {
        "distribution": category_charts,
        "trend": [],
        "comparison": [],
        "lifecycle": lifecycle_charts,
        "category": category_charts,
        "efficiency": eff_series,
        "stage_distribution": stage_distribution,
        "efficiency_kpis": efficiency_kpis,
    }

    dynamics: List[DynamicData] = _recent_dynamics(db, limit=15)

    return APIResponse(
        data=DashboardResponse(
            metrics=metrics,
            charts=charts,
            dynamics=dynamics,
        )
    )
