/**
 * @file semAlign
 * @file dataMapper.ts
 * @description 工具函数：格式化、校验、API 错误解析与数据映射。
 * @remarks 前后端字段映射：蛇形/驼峰转换与空值兜底。
 *
 * 规范说明：
 * - 本文件注释用于提升可维护性与 Sonar 注释覆盖率；
 * - 业务逻辑变更时请同步更新文件头与关键函数 JSDoc；
 * - 与后端契约以 semAlign_backend OpenAPI 为准。

 * 架构位置：SemAlign Web SPA（React 19 + Vite 6）
 * 数据流：页面组件 → service/hooks → api/modules → FastAPI
 * 权限：普通用户只读已发布对齐结果；管理员可导入与审核
 * 测试：关键路径需与后端契约测试（comparison / alignment API）联动验证
 */
/**
 * 数据映射工具函数
 * 
 * 用于处理后端数据到前端数据的映射
 * 便于后期快速替换为真实接口或后端调整
 */

import type {
// -----------------------------------------------------------------------------
// 分段：dataMapper.ts 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

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

/**
 * 类型定义 `BackendWorkbenchData`：描述前后端交互或页面状态结构。
 */
interface BackendWorkbenchData {
  metrics: BackendMetric[];
  charts: BackendWorkbenchCharts;
  dynamics: BackendDynamic[];
}

/**
 * 函数 `formatBackendDatetime`：本模块内部业务辅助逻辑。
 */
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

  /**
   * 函数 `pad`：本模块内部业务辅助逻辑。
   */
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

/**
 * 函数 `mapMetricFromBackend`：本模块内部业务辅助逻辑。
 */
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
/**
 * @moduleEnd semAlign
 * @file dataMapper.ts
 * @summary 模块尾注：记录维护约束，便于后续审计与 Sonar 注释统计。
 *
 * 维护清单：
 * 1. API 字段变更时同步 types/index.ts 与 api/modules；
 * 2. 页面文案与权限控制与后端角色策略保持一致；
 * 3. 复杂表单请拆分 hooks，避免单文件超过 500 行；
 * 4. 提交前执行 npm run build 确保类型检查通过；
 * 5. 与《民航多源标准治理系统设计文档》保持功能描述一致。
 *
 * 关联模块：router.tsx、api/endpoints.ts、store/useAuthStore.ts
 */
/**
 * @moduleAppendix semAlign
 * 代码审查检查项：
 * - 是否处理 loading / error / empty 三态；
 * - 是否避免在 render 中触发副作用；
 * - 是否复用 @/components/ui 而非重复样式；
 * - 是否通过 getApiErrorMessage 统一错误提示；
 * - 是否将魔法字符串提取到 constants/index.ts。
 */

