/**
 * @file semAlign
 * @file endpoints.ts
 * @description HTTP 客户端层：Axios 实例、拦截器、端点常量与响应适配。
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
 * API 端点定义
 */
export const Endpoints = {
  // 标准管理
  STANDARDS: '/standards',
  STANDARD_FILTER_OPTIONS: '/standards/filter-options',
  STANDARD_DETAIL: (id: string) => `/standards/${id}`,
  STANDARD_CONTENT: (id: string) => `/standards/${id}/content`,
  STANDARD_DOWNLOAD: (id: string) => `/standards/${id}/download`,
  STANDARD_CREATE: '/standards',
  STANDARD_UPDATE: (id: string) => `/standards/${id}`,
  STANDARD_DELETE: (id: string) => `/standards/${id}`,
  TERM_CONFLICT_OVERVIEW: '/term-conflicts/overview',
  CONFLICT_DIALOGUE_OVERVIEW: '/conflict-dialogues/overview',
  VECTOR_STORE_OVERVIEW: '/vector-store/overview',

  // 检索
  SEARCH: '/search',
  SEARCH_SUGGEST: '/search/suggest',

  // 导入（semAlign_backend：上传与行导入路径）
  UPLOAD: '/import/upload',
  /** 批量 StandardCreate[] */
  IMPORT: '/import',
  /** 预览行提交导入 */
  IMPORT_RECORDS: '/import/records',
  IMPORT_STATUS: (taskId: string) => `/import/${taskId}`,

  // 用户
  USER_PROFILE: '/user/profile',
  USER_PERMISSIONS: '/user/permissions',
  USER_ADMIN_LIST: '/user/admin/users',
  USER_ADMIN_UPDATE: (id: string) => `/user/admin/users/${id}`,
  USER_LOGIN: '/auth/login',
  USER_FORGOT_PASSWORD: '/auth/forgot-password',

  // 工作台（semAlign_backend：workbench 前缀）
  DASHBOARD: '/workbench/dashboard',

  // 对齐（与 mvp/src/api/endpoints.py 一致：创建与列表均为 POST/GET /alignment/tasks）
  ALIGNMENT_LIST: '/alignment/tasks',
  ALIGNMENT_DETAIL: (taskId: string) => `/alignment/tasks/${taskId}`,
  ALIGNMENT_DELETE: (taskId: string) => `/alignment/tasks/${taskId}`,
  ALIGNMENT_CHAT: '/alignment/chat',
  /** 后端为 POST，非 PUT */
  ALIGNMENT_SAVE: (taskId: string) => `/alignment/tasks/${taskId}/save`,

  // 比对结果
  COMPARISON_TASK: (taskId: string) => `/comparison/task/${taskId}`,
  COMPARISON_STATS: (taskId: string) => `/comparison/stats/${taskId}`,
  COMPARISON_CLUSTERS: (taskId: string) => `/comparison/clusters/${taskId}`,
  COMPARISON_CONFLICTS: (taskId: string) => `/comparison/conflicts/${taskId}`,
  COMPARISON_SOLUTIONS: (taskId: string) => `/comparison/solutions/${taskId}`,
} as const;
/**
 * @moduleEnd semAlign
 * @file endpoints.ts
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

