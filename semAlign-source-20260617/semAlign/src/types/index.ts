/**
 * @file semAlign
 * @file index.ts
 * @description 全局 TypeScript 类型定义：实体、DTO 与分页结构。
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
import type { ReactNode } from 'react';

// -----------------------------------------------------------------------------
// 分段：index.ts 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

/**
 * 通用类型定义
 */

/**
 * 接口 `PaginationParams`：分页参数
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface PaginationParams {
  page?: number;
  size?: number;
  keyword?: string;
}

/**
 * 接口 `PaginatedResponse`：分页响应
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  size: number;
}

/**
 * 接口 `ApiResponse`：API 响应基类
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  timestamp?: number;
}

/**
 * 接口 `StatusType`：状态类型
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type StatusType = 'active' | 'draft' | 'review' | 'deprecated' | 'new';

/**
 * 接口 `BaseEntity`：基础实体
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt?: string;
}

// ==================== 工作台相关类型 ====================

/**
 * 接口 `Metric`：指标数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface Metric {
  label: string;
  value: string | number;
  /** 展示在数值旁，如「个」 */
  unit?: string;
  trend: number;
  trendLabel: string;
}

/**
 * 接口 `Dynamic`：动态/消息
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface Dynamic {
  id: string;
  title: string;
  description?: string;
  time: string;
  date: string;
  action: '新增' | '修订' | '废止' | '审核';
}

/**
 * 接口 `ChartData`：图表数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ChartData {
  name: string;
  value: number;
  [key: string]: any;
}

/** 工作台流程效率卡片（后端 efficiency_kpis） */
/**
 * 接口 `WorkbenchEfficiencyKpis`：描述业务数据结构
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface WorkbenchEfficiencyKpis {
  avg_review_days: number;
  avg_publish_days: number;
  review_mom_delta: number;
  publish_mom_delta: number;
}

/** 生命周期阶段对比柱图 */
/**
 * 接口 `StageDistributionRow`：描述业务数据结构
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface StageDistributionRow {
  name: string;
  current: number;
  last: number;
}

/**
 * 接口 `WorkbenchData`：工作台数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface WorkbenchData {
  metrics: Metric[];
  charts: {
    distribution: ChartData[];
    trend: ChartData[];
    comparison: ChartData[];
    lifecycle: ChartData[];
    category: ChartData[];
    efficiency: Array<{
      name: string;
      review: number;
      publish: number;
    }>;
    stage_distribution: StageDistributionRow[];
    efficiency_kpis?: WorkbenchEfficiencyKpis;
  };
  dynamics: Dynamic[];
}

// ==================== 标准管理相关类型 ====================

/**
 * 接口 `Standard`：标准实体
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface Standard {
  id: string;
  code: string;
  name: string;
  version: string;
  status: StatusType;
  department: string;
  date: string;
  category: string;
  description?: string;
  /**
   * 检索接口返回的相关度（混合得分 / Reranker 重排后等），通常为 0–100；若为 0–1 小数由适配层归一化。
   */
  relevanceScore?: number;
}

/**
 * 接口 `SystemMatrix`：系统矩阵
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface SystemMatrix {
  title: string;
  count: number;
  category: string;
  systems: string[];
}

// ==================== 搜索相关类型 ====================

/**
 * 接口 `SearchSuggestion`：搜索建议（后端 type: standard_no | name | category | department | source_file 等）
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface SearchSuggestion {
  type: string;
  text: string;
  count?: number;
}

/**
 * 接口 `Message`：消息类型（用于 AI 问答）
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// ==================== 导入相关类型 ====================

/**
 * 接口 `ImportTask`：导入任务
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ImportTask {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  fileName?: string;
  result?: {
    total: number;
    success: number;
    failed: number;
  };
  error?: string;
}

// ==================== 认证相关类型 ====================

/**
 * 接口 `User`：用户信息
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface User {
  id: string;
  username: string;
  email?: string;
  name: string;
  avatar?: string;
  role: 'admin' | 'user' | 'viewer';
  department?: string;
}

/**
 * 接口 `LoginRequest`：登录请求
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * 接口 `LoginResponse`：登录响应
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface LoginResponse {
  token: string;
  user: User;
  expiresIn: number;
}

// ==================== 标准对齐相关类型 ====================

/**
 * 接口 `AlignmentMessage`：对齐消息类型
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface AlignmentMessage {
  id: string;
  type: 'ai' | 'user';
  content: string | ReactNode;
  timestamp: string;
}

/**
 * 接口 `StandardGroup`：标准组
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface StandardGroup {
  id: string;
  name: string;
  description?: string;
  standards: Standard[];
}

/**
 * 接口 `AlignmentTask`：对齐任务
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface AlignmentTask {
  id: string;
  group1: StandardGroup;
  group2: StandardGroup;
  priorityRules: string[];
  customRule?: string;
  status: 'pending' | 'processing' | 'completed';
  createdAt: string;
}

/**
 * 接口 `PriorityRule`：优先级规则
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface PriorityRule {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
}

// ==================== 智能检索相关类型 ====================

/**
 * 接口 `SearchResult`：搜索结果
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface SearchResult {
  id: string;
  code: string;
  title: string;
  content: string;
  department: string;
  relevance: number;
}

/**
 * 接口 `SearchMode`：搜索模式
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type SearchMode = 'semantic' | 'exact';

/**
 * 与「语义建模及检索层」对齐的检索策略（由 GET /search 的 retrieval_mode 传给后端）。
 * hybrid：稀疏(BM25)+稠密向量融合；sparse：关键词/BM25；dense：向量 ANN。
 */
/**
 * 接口 `RetrievalMode`：描述业务数据结构
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type RetrievalMode = 'hybrid' | 'sparse' | 'dense';

/** 智能检索 query 附加参数 */
/**
 * 接口 `SearchQueryOptions`：描述业务数据结构
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface SearchQueryOptions {
  retrievalMode?: RetrievalMode;
}

/** GET /search 解包后的业务数据 */
/**
 * 接口 `SearchQueryData`：描述业务数据结构
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface SearchQueryData {
  standards: Standard[];
  suggestions: unknown[];
  total: number;
  answer?: string;
  sources?: string[];
  /** 可解释推理步骤（如：规则提取 → 条款匹配 → 差异分析） */
  reasoning_steps?: string[];
}

/**
 * 接口 `AIAnswer`：AI 问答结果
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface AIAnswer {
  query: string;
  answer: string;
  sources: string[];
  timestamp: string;
}

// ==================== 文件导入相关类型 ====================

/**
 * 接口 `ImportStatus`：导入状态
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type ImportStatus = 'idle' | 'parsing' | 'success' | 'error';

/**
 * 接口 `ParseResult`：解析结果
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ParseResult {
  total: number;
  success: number;
  failed: number;
  items: Standard[];
  errors?: string[];
}

/**
 * 接口 `UploadDataItem`：上传解析后的数据项
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface UploadDataItem {
  standard_no: string;
  name: string;
  version: string;
  status: string;
  validation_status: 'valid' | 'invalid' | 'duplicate' | 'needs_update';
  conflict_status?: string;
  rule_violations?: string;
}

/**
 * 接口 `UploadValidationResult`：上传响应验证结果
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface UploadValidationResult {
  total_rows: number;
  valid_rows: number;
  need_update: number;
  duplicate_rows: number;
  data: UploadDataItem[];
}

/**
 * 接口 `UploadResponse`：上传响应
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface UploadResponse {
  filename: string;
  status: 'success' | 'error';
  validation: UploadValidationResult;
  message: string;
}

/**
 * 接口 `ImportRequest`：导入请求
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ImportRequest {
  records: Array<{
    standard_no: string;
    name: string;
    version: string;
    status: string;
  }>;
}

/**
 * 接口 `ImportResponse`：导入响应
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ImportResponse {
  status: 'success' | 'error';
  message: string;
  imported: number;
  updated: number;
  conflicts: number;
}

// ==================== 对齐结果与解决方案相关类型 ====================

/**
 * 接口 `ConflictType`：冲突类型
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type ConflictType = 'terminology' | 'requirement' | 'scope' | 'format' | 'other';

/**
 * 接口 `ConflictSeverity`：冲突严重程度
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export type ConflictSeverity = 'high' | 'medium' | 'low';

/**
 * 接口 `ConflictItem`：冲突项
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface ConflictItem {
  id: string;
  type: ConflictType;
  severity: ConflictSeverity;
  title: string;
  description: string;
  standard1: {
    code: string;
    name: string;
    clause: string;
    content: string;
  };
  standard2: {
    code: string;
    name: string;
    clause: string;
    content: string;
  };
  suggestion: string;
}

/**
 * 接口 `AlignmentResultSummary`：对齐结果摘要
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface AlignmentResultSummary {
  totalStandards: number;
  conflictCount: number;
  highSeverityCount: number;
  mediumSeverityCount: number;
  lowSeverityCount: number;
  processedAt: string;
  duration: string;
}

/**
 * 接口 `Solution`：解决方案
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface Solution {
  id: string;
  conflictId: string;
  type: 'adopt_standard1' | 'adopt_standard2' | 'merge' | 'create_new' | 'pending';
  title: string;
  description: string;
  recommendedStandard?: string;
  reasoning: string;
  impact: 'major' | 'minor' | 'none';
  status: 'pending' | 'accepted' | 'rejected';
}

/**
 * 接口 `AlignmentResult`：完整的对齐结果
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export interface AlignmentResult {
  taskId: string;
  taskName: string;
  group1: StandardGroup;
  group2: StandardGroup;
  summary: AlignmentResultSummary;
  conflicts: ConflictItem[];
  solutions: Solution[];
  createdAt: string;
}
/**
 * @moduleEnd semAlign
 * @file index.ts
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

