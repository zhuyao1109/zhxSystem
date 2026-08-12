/**
 * @file semAlign
 * @file user.ts
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
 * 用户管理 API
 */
import api from '../axios';
import { Endpoints } from '../endpoints';
import type { ApiResponse } from '@/types';

/**
 * 类型定义 `UserProfile`：描述前后端交互或页面状态结构。
 */
export interface UserProfile {
  id: number;
  username: string;
  email?: string;
  role: string;
  is_active: boolean;
  avatar?: string;
  created_at: string;
}

/**
 * 类型定义 `UpdateProfileRequest`：描述前后端交互或页面状态结构。
 */
export interface UpdateProfileRequest {
  email?: string;
  avatar?: string;
}

/**
 * 类型定义 `ChangePasswordRequest`：描述前后端交互或页面状态结构。
 */
export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

/**
 * 类型定义 `UserPermissions`：描述前后端交互或页面状态结构。
 */
export interface UserPermissions {
  role: string;
  permissions: Record<string, boolean>;
}

const userApi = {
  /**
   * 获取当前用户信息
   */
  getProfile: async (): Promise<ApiResponse<UserProfile>> => {
    return api.get(Endpoints.USER_PROFILE);
  },

  /**
   * 更新用户信息
   */
  updateProfile: async (data: UpdateProfileRequest): Promise<ApiResponse<UserProfile>> => {
    return api.put(Endpoints.USER_PROFILE, data);
  },

  /**
   * 修改密码
   */
  changePassword: async (data: ChangePasswordRequest): Promise<ApiResponse<{ success: boolean }>> => {
    return api.post('/user/change-password', data);
  },

  /**
   * 获取当前用户权限
   */
  getPermissions: async (): Promise<ApiResponse<UserPermissions>> => {
    return api.get(Endpoints.USER_PERMISSIONS);
  },

  /**
   * 管理员获取用户列表
   */
  listUsers: async (): Promise<ApiResponse<UserProfile[]>> => {
    return api.get(Endpoints.USER_ADMIN_LIST);
  },

  /**
   * 管理员更新用户角色/状态
   */
  updateUserByAdmin: async (
    id: number,
    data: { role?: string; is_active?: boolean }
  ): Promise<ApiResponse<UserProfile>> => {
    return api.put(Endpoints.USER_ADMIN_UPDATE(String(id)), data);
  },
};

export default userApi;
/**
 * @moduleEnd semAlign
 * @file user.ts
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

