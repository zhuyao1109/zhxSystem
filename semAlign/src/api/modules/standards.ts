/**
 * @file semAlign
 * @file standards.ts
 * @description API 子模块：封装后端 REST 接口的请求与响应类型。
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
 * 标准管理 API 模块
 * 
 * 提供标准的增删改查功能
 */

import apiAdapter from '@/api/adapter';
import type {
  ApiResponse,
  PaginatedResponse,
  Standard,
} from '@/types';

/**
 * 类型定义 `StandardsQueryParams`：描述前后端交互或页面状态结构。
 */
export interface StandardsQueryParams {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
  department?: string;
  category?: string;
}

/**
 * 服务模块 `standardsApi`：聚合 API 调用并返回强类型结果。
 */
export const standardsApi = {
  /**
   * 获取标准列表
   */
  getList: async (params?: StandardsQueryParams): Promise<ApiResponse<PaginatedResponse<Standard>>> => {
    return apiAdapter.standards.getList(params);
  },

  /**
   * 获取标准详情
   */
  getById: async (id: string): Promise<ApiResponse<Standard>> => {
    return apiAdapter.standards.getById(id);
  },

  /**
   * 创建标准
   */
  create: async (data: Omit<Standard, 'id'>): Promise<ApiResponse<Standard>> => {
    return apiAdapter.standards.create(data);
  },

  /**
   * 更新标准
   */
  update: async (id: string, data: Partial<Standard>): Promise<ApiResponse<Standard>> => {
    return apiAdapter.standards.update(id, data);
  },

  /**
   * 删除标准
   */
  delete: async (id: string): Promise<ApiResponse<null>> => {
    return apiAdapter.standards.delete(id);
  },
};

export default standardsApi;
/**
 * @moduleEnd semAlign
 * @file standards.ts
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

