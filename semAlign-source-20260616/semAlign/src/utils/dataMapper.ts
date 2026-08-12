/**
 * 数据映射工具函数
 * 
 * 用于处理后端数据到前端数据的映射
 * 便于后期快速替换为真实接口或后端调整
 */

import type {
  Standard,
  Metric,
  Dynamic,
  WorkbenchData,
  ChartData,
} from '@/types';

// ==================== 后端类型定义 ====================

/**
 * 后端标准对象类型
 */
export interface BackendStandard {
  id: number;
  standard_no: string; // 前端期望: code
  name: string;
  version: string;
  status: string;
  category?: string;
  department?: string;
  description?: string;
  created_at: string; // 前端期望: date
  updated_at?: string;
  is_active?: boolean;
  rule_violations?: string | null;
  conflict_status?: string | null;
  source_file?: string | null;
}

/**
 * 后端 Metric 类型
 */
interface BackendMetric {
  title: string; // 前端期望: label
  value: number;
  unit?: string;
  trend?: number;
}

/**
 * 后端 Dynamic 类型
 */
interface BackendDynamic {
  id: string;
  type: string;
  description?: string;
  time: string; // 前端期望: date
}

/**
 * 后端工作台数据类型
 */
interface BackendWorkbenchCharts {
  distribution: ChartData[];
  trend: ChartData[];
  comparison: ChartData[];
  lifecycle: ChartData[];
  category: ChartData[];
  efficiency: Array<Record<string, unknown>>;
  stage_distribution?: Array<{ name: string; current: number; last: number }>;
  efficiency_kpis?: {
    avg_review_days: number;
    avg_publish_days: number;
    review_mom_delta: number;
    publish_mom_delta: number;
  };
}

interface BackendWorkbenchData {
  metrics: BackendMetric[];
  charts: BackendWorkbenchCharts;
  dynamics: BackendDynamic[];
}

function formatBackendDatetime(value?: string): string {
  if (!value) {
    return '';
  }

  const normalized = value.trim().replace(' ', 'T');
  // 后端若未携带时区（SQLite 常见），按 UTC 解释再转为浏览器本地时间
  const hasTimezone = /[zZ]$|[+-]\d{2}:\d{2}$/.test(normalized);
  const iso = hasTimezone ? normalized : `${normalized}Z`;
  const d = new Date(iso);

  if (Number.isNaN(d.getTime())) {
    return value;
  }

  const pad = (n: number) => String(n).padStart(2, '0');
  const y = d.getFullYear();
  const m = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hh = pad(d.getHours());
  const mm = pad(d.getMinutes());
  const ss = pad(d.getSeconds());
  return `${y}-${m}-${day} ${hh}:${mm}:${ss}`;
}

// ==================== 映射函数 ====================

/**
 * 映射标准对象（后端 -> 前端）
 */
export function mapStandardFromBackend(backendStandard: BackendStandard): Standard {
  // 状态值映射：中文 -> 英文
  const statusMap: Record<string, Standard['status']> = {
    '有效': 'active',
    '草稿': 'draft',
    '审核中': 'review',
    '已废止': 'deprecated',
    '新增': 'new',
  };

  return {
    id: String(backendStandard.id),
    code: backendStandard.standard_no, // standard_no -> code
    name: backendStandard.name,
    version: backendStandard.version,
    status: statusMap[backendStandard.status] || backendStandard.status as Standard['status'],
    department: backendStandard.department || '',
    date: formatBackendDatetime(backendStandard.created_at), // created_at(UTC) -> 本地时间展示
    category: backendStandard.category || '',
    description: backendStandard.description,
  };
}

/**
 * 映射标准对象数组（后端 -> 前端）
 */
export function mapStandardsFromBackend(backendStandards: BackendStandard[]): Standard[] {
  return backendStandards.map(mapStandardFromBackend);
}

/**
 * 映射 Metric 对象（后端 -> 前端）
 */
function trendLabelForMetric(trend: number): string {
  if (trend === 0) {
    return '';
  }
  return trend > 0 ? '环比增长' : '环比下降';
}

export function mapMetricFromBackend(backendMetric: BackendMetric): Metric {
  const trend = backendMetric.trend ?? 0;
  return {
    label: backendMetric.title, // title -> label
    value: backendMetric.value,
    unit: backendMetric.unit,
    trend,
    trendLabel: trendLabelForMetric(trend),
  };
}

/**
 * 映射 Metric 数组（后端 -> 前端）
 */
export function mapMetricsFromBackend(backendMetrics: BackendMetric[]): Metric[] {
  return backendMetrics.map(mapMetricFromBackend);
}

/**
 * 映射 Dynamic 对象（后端 -> 前端）
 */
export function mapDynamicFromBackend(backendDynamic: BackendDynamic): Dynamic {
  // 根据 type 映射到 action
  const actionMap: Record<string, Dynamic['action']> = {
    import: '新增',
    alignment: '修订',
    delete: '废止',
    create: '新增',
    update: '修订',
  };

  return {
    id: backendDynamic.id,
    title: backendDynamic.description || backendDynamic.type,
    description: backendDynamic.description,
    time: backendDynamic.time,
    date: backendDynamic.time, // time -> date
    action: actionMap[backendDynamic.type] || '新增',
  };
}

/**
 * 映射 Dynamic 数组（后端 -> 前端）
 */
export function mapDynamicsFromBackend(backendDynamics: BackendDynamic[]): Dynamic[] {
  return backendDynamics.map(mapDynamicFromBackend);
}

/**
 * 映射工作台数据（后端 -> 前端）
 */
export function mapWorkbenchFromBackend(backendData: BackendWorkbenchData): WorkbenchData {
  const eff = backendData.charts.efficiency ?? [];
  const stages = backendData.charts.stage_distribution ?? [];
  return {
    metrics: mapMetricsFromBackend(backendData.metrics),
    charts: {
      ...backendData.charts,
      efficiency: eff.map((item: Record<string, unknown>) => ({
        name: String(item.name ?? ''),
        review: Number(item.review ?? 0),
        publish: Number(item.publish ?? 0),
      })),
      stage_distribution: stages.map((row) => ({
        name: row.name,
        current: row.current,
        last: row.last,
      })),
      efficiency_kpis: backendData.charts.efficiency_kpis,
    },
    dynamics: mapDynamicsFromBackend(backendData.dynamics ?? []),
  };
}

/**
 * 映射标准对象（前端 -> 后端）
 */
export function mapStandardToBackend(frontendStandard: Partial<Standard>): Partial<BackendStandard> {
  // 状态值映射：英文 -> 中文
  const statusMap: Record<Standard['status'], string> = {
    'active': '有效',
    'draft': '草稿',
    'review': '审核中',
    'deprecated': '已废止',
    'new': '新增',
  };

  const backendStandard: Partial<BackendStandard> = {};

  if (frontendStandard.code !== undefined) {
    backendStandard.standard_no = frontendStandard.code; // code -> standard_no
  }
  if (frontendStandard.name !== undefined) {
    backendStandard.name = frontendStandard.name;
  }
  if (frontendStandard.version !== undefined) {
    backendStandard.version = frontendStandard.version;
  }
  if (frontendStandard.status !== undefined) {
    backendStandard.status = statusMap[frontendStandard.status] || frontendStandard.status;
  }
  if (frontendStandard.department !== undefined) {
    backendStandard.department = frontendStandard.department;
  }
  if (frontendStandard.category !== undefined) {
    backendStandard.category = frontendStandard.category;
  }
  if (frontendStandard.description !== undefined) {
    backendStandard.description = frontendStandard.description;
  }

  return backendStandard;
}

/**
 * 映射标准对象数组（前端 -> 后端）
 */
export function mapStandardsToBackend(frontendStandards: Partial<Standard>[]): Partial<BackendStandard>[] {
  return frontendStandards.map(mapStandardToBackend);
}

// ==================== 工具函数 ====================

/**
 * 检查是否为后端标准对象
 */
export function isBackendStandard(obj: any): obj is BackendStandard {
  return obj && typeof obj === 'object' && 'standard_no' in obj;
}

/**
 * 检查是否为前端标准对象
 */
export function isFrontendStandard(obj: any): obj is Standard {
  return obj && typeof obj === 'object' && 'code' in obj;
}

/**
 * 自动映射标准对象（根据类型自动选择映射方向）
 */
export function autoMapStandard(obj: any): Standard | BackendStandard {
  if (isBackendStandard(obj)) {
    return mapStandardFromBackend(obj);
  }
  if (isFrontendStandard(obj)) {
    return mapStandardToBackend(obj) as BackendStandard;
  }
  throw new Error('Invalid standard object type');
}
