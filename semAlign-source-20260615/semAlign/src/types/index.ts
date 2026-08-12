import type { ReactNode } from 'react';

/**
 * 通用类型定义
 */

// 分页参数
export interface PaginationParams {
  page?: number;
  size?: number;
  keyword?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  size: number;
}

// API 响应基类
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  timestamp?: number;
}

// 状态类型
export type StatusType = 'active' | 'draft' | 'review' | 'deprecated' | 'new';

// 基础实体
export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt?: string;
}

// ==================== 工作台相关类型 ====================

// 指标数据
export interface Metric {
  label: string;
  value: string | number;
  /** 展示在数值旁，如「个」 */
  unit?: string;
  trend: number;
  trendLabel: string;
}

// 动态/消息
export interface Dynamic {
  id: string;
  title: string;
  description?: string;
  time: string;
  date: string;
  action: '新增' | '修订' | '废止' | '审核';
}

// 图表数据
export interface ChartData {
  name: string;
  value: number;
  [key: string]: any;
}

/** 工作台流程效率卡片（后端 efficiency_kpis） */
export interface WorkbenchEfficiencyKpis {
  avg_review_days: number;
  avg_publish_days: number;
  review_mom_delta: number;
  publish_mom_delta: number;
}

/** 生命周期阶段对比柱图 */
export interface StageDistributionRow {
  name: string;
  current: number;
  last: number;
}

// 工作台数据
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

// 标准实体
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

// 系统矩阵
export interface SystemMatrix {
  title: string;
  count: number;
  category: string;
  systems: string[];
}

// ==================== 搜索相关类型 ====================

// 搜索建议（后端 type: standard_no | name | category | department | source_file 等）
export interface SearchSuggestion {
  type: string;
  text: string;
  count?: number;
}

// 消息类型（用于 AI 问答）
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// ==================== 导入相关类型 ====================

// 导入任务
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

// 用户信息
export interface User {
  id: string;
  username: string;
  email?: string;
  name: string;
  avatar?: string;
  role: 'admin' | 'user' | 'viewer';
  department?: string;
}

// 登录请求
export interface LoginRequest {
  username: string;
  password: string;
}

// 登录响应
export interface LoginResponse {
  token: string;
  user: User;
  expiresIn: number;
}

// ==================== 标准对齐相关类型 ====================

// 对齐消息类型
export interface AlignmentMessage {
  id: string;
  type: 'ai' | 'user';
  content: string | ReactNode;
  timestamp: string;
}

// 标准组
export interface StandardGroup {
  id: string;
  name: string;
  description?: string;
  standards: Standard[];
}

// 对齐任务
export interface AlignmentTask {
  id: string;
  group1: StandardGroup;
  group2: StandardGroup;
  priorityRules: string[];
  customRule?: string;
  status: 'pending' | 'processing' | 'completed';
  createdAt: string;
}

// 优先级规则
export interface PriorityRule {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
}

// ==================== 智能检索相关类型 ====================

// 搜索结果
export interface SearchResult {
  id: string;
  code: string;
  title: string;
  content: string;
  department: string;
  relevance: number;
}

// 搜索模式
export type SearchMode = 'semantic' | 'exact';

/**
 * 与「语义建模及检索层」对齐的检索策略（由 GET /search 的 retrieval_mode 传给后端）。
 * hybrid：稀疏(BM25)+稠密向量融合；sparse：关键词/BM25；dense：向量 ANN。
 */
export type RetrievalMode = 'hybrid' | 'sparse' | 'dense';

/** 智能检索 query 附加参数 */
export interface SearchQueryOptions {
  retrievalMode?: RetrievalMode;
}

/** GET /search 解包后的业务数据 */
export interface SearchQueryData {
  standards: Standard[];
  suggestions: unknown[];
  total: number;
  answer?: string;
  sources?: string[];
  /** 可解释推理步骤（如：规则提取 → 条款匹配 → 差异分析） */
  reasoning_steps?: string[];
}

// AI 问答结果
export interface AIAnswer {
  query: string;
  answer: string;
  sources: string[];
  timestamp: string;
}

// ==================== 文件导入相关类型 ====================

// 导入状态
export type ImportStatus = 'idle' | 'parsing' | 'success' | 'error';

// 解析结果
export interface ParseResult {
  total: number;
  success: number;
  failed: number;
  items: Standard[];
  errors?: string[];
}

// 上传解析后的数据项
export interface UploadDataItem {
  standard_no: string;
  name: string;
  version: string;
  status: string;
  validation_status: 'valid' | 'invalid' | 'duplicate' | 'needs_update';
  conflict_status?: string;
  rule_violations?: string;
}

// 上传响应验证结果
export interface UploadValidationResult {
  total_rows: number;
  valid_rows: number;
  need_update: number;
  duplicate_rows: number;
  data: UploadDataItem[];
}

// 上传响应
export interface UploadResponse {
  filename: string;
  status: 'success' | 'error';
  validation: UploadValidationResult;
  message: string;
}

// 导入请求
export interface ImportRequest {
  records: Array<{
    standard_no: string;
    name: string;
    version: string;
    status: string;
  }>;
}

// 导入响应
export interface ImportResponse {
  status: 'success' | 'error';
  message: string;
  imported: number;
  updated: number;
  conflicts: number;
}

// ==================== 对齐结果与解决方案相关类型 ====================

// 冲突类型
export type ConflictType = 'terminology' | 'requirement' | 'scope' | 'format' | 'other';

// 冲突严重程度
export type ConflictSeverity = 'high' | 'medium' | 'low';

// 冲突项
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

// 对齐结果摘要
export interface AlignmentResultSummary {
  totalStandards: number;
  conflictCount: number;
  highSeverityCount: number;
  mediumSeverityCount: number;
  lowSeverityCount: number;
  processedAt: string;
  duration: string;
}

// 解决方案
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

// 完整的对齐结果
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
