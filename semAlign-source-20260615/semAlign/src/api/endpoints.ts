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
