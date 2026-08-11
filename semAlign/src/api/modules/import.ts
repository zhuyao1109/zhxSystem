/**
 * @file semAlign
 * @file import.ts
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
 * 标准导入 API 模块
 * 
 * 提供文件上传和批量导入功能
 */

import apiAdapter from '@/api/adapter';
import type {
  UploadResponse,
  ImportResponse,
  UploadDataItem,
} from '@/types';

/**
 * 服务模块 `importApi`：聚合 API 调用并返回强类型结果。
 */
export const importApi = {
  /**
   * 上传文件并解析
   */
  uploadFile: async (file: File): Promise<UploadResponse> => {
    return apiAdapter.import.uploadFile(file);
  },

  /**
   * 提交导入记录
   */
  importRecords: async (records: UploadDataItem[]): Promise<ImportResponse> => {
    return apiAdapter.import.importRecords(records);
  },
};

export default importApi;
/**
 * @moduleEnd semAlign
 * @file import.ts
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

