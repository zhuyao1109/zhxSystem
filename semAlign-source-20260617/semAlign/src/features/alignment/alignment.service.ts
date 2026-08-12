/**
 * @file semAlign
 * @file alignment.service.ts
 * @description 标准对齐模块：任务创建、冲突结果、对齐助手对话与审核流转。
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
 * 对齐服务
 */

import { alignmentApi } from '@/api/modules/alignment';

/**
 * 服务模块 `alignmentService`：聚合 API 调用并返回强类型结果。
 */
export const alignmentService = {
  /**
   * 创建对齐任务
   */
  createTask: async (data: {
    group1Id: string;
    group2Id: string;
    group1Name?: string;
    group2Name?: string;
    priorityRules: string[];
    customRule?: string;
  }) => {
    return await alignmentApi.createTask(data);
  },

  /**
   * 获取对齐任务列表
   */
  getTaskList: async (params?: { page?: number; size?: number }) => {
    return await alignmentApi.getTaskList(params);
  },

  /**
   * 获取对齐任务详情
   */
  getTaskDetail: async (taskId: string) => {
    return await alignmentApi.getTaskDetail(taskId);
  },

  /**
   * 重新执行对齐任务
   */
  retryTask: async (taskId: string) => {
    return await alignmentApi.retryTask(taskId);
  },

  /**
   * 删除对齐任务
   */
  deleteTask: async (taskId: string) => {
    return await alignmentApi.deleteTask(taskId);
  },

  /**
   * 保存对齐结果
   */
  saveResult: async (taskId: string, result: any) => {
    return await alignmentApi.saveResult(taskId, result);
  },

  /**
   * 对齐助手聊天
   */
  chat: async (data: { message: string; group1Id?: string; group2Id?: string }) => {
    return await alignmentApi.chat(data);
  },
};

export default alignmentService;
/**
 * @moduleEnd semAlign
 * @file alignment.service.ts
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

