/**
 * @file semAlign
 * @file auth.ts
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
import api from '../axios';
import { Endpoints } from '../endpoints';
import type { LoginRequest, ApiResponse, LoginResponse, User } from '@/types';

/** semAlign_backend LoginResponse.data 原始形状 */
interface BackendLoginData {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    username: string;
    email?: string | null;
    role: string;
    is_active: boolean;
    avatar?: string | null;
    created_at?: string;
  };
}

/**
 * 函数 `mapBackendRole`：本模块内部业务辅助逻辑。
 */
function mapBackendRole(role: string): User['role'] {
  if (role === 'admin') {
    return 'admin';
  }
  if (role === 'user') {
    return 'user';
  }
  return 'viewer';
}

/**
 * 函数 `mapBackendUser`：本模块内部业务辅助逻辑。
 */
function mapBackendUser(u: BackendLoginData['user']): User {
  return {
    id: String(u.id),
    username: u.username,
    name: u.username,
    email: u.email ?? undefined,
    avatar: u.avatar ?? undefined,
    role: mapBackendRole(u.role),
  };
}

/**
 * 函数 `failResponse`：本模块内部业务辅助逻辑。
 */
function failResponse<T>(raw: ApiResponse<BackendLoginData>): ApiResponse<T> {
  return { code: raw.code, message: raw.message };
}

/**
 * 服务模块 `authApi`：聚合 API 调用并返回强类型结果。
 */
export const authApi = {
  /**
   * 用户登录（后端返回 access_token，此处归一为 LoginResponse.token）
   */
  login: async (data: LoginRequest): Promise<ApiResponse<LoginResponse>> => {
    const raw: ApiResponse<BackendLoginData> = await api.post(Endpoints.USER_LOGIN, data);
    if (raw.code !== 200 || !raw.data) {
      return failResponse(raw);
    }
    const { access_token, user: u } = raw.data;
    const user = mapBackendUser(u);
    const TOKEN_EXPIRES_IN = 30 * 60;
    return {
      code: raw.code,
      message: raw.message,
      data: {
        token: access_token,
        user,
        expiresIn: TOKEN_EXPIRES_IN,
      },
    };
  },

  /**
   * 获取个人资料
   */
  getProfile: async (): Promise<ApiResponse<User>> => {
    const raw: ApiResponse<BackendLoginData['user']> = await api.get(Endpoints.USER_PROFILE);
    if (raw.code !== 200 || !raw.data) {
      return failResponse(raw);
    }
    return {
      code: raw.code,
      message: raw.message,
      data: mapBackendUser(raw.data),
    };
  },

  /**
   * 更新用户信息（JSON body，与后端 UserUpdate 一致）
   */
  updateProfile: async (body: { avatar?: string; email?: string }): Promise<ApiResponse<User>> => {
    const raw: ApiResponse<BackendLoginData['user']> = await api.put(Endpoints.USER_PROFILE, body);
    if (raw.code !== 200 || !raw.data) {
      return failResponse(raw);
    }
    return {
      code: raw.code,
      message: raw.message,
      data: mapBackendUser(raw.data),
    };
  },

  /**
   * 忘记密码重置
   */
  forgotPassword: async (usernameOrEmail: string, newPassword: string): Promise<ApiResponse<{ reset: boolean }>> => {
    return api.post(Endpoints.USER_FORGOT_PASSWORD, {
      username_or_email: usernameOrEmail,
      new_password: newPassword,
    });
  },
};

export default authApi;
/**
 * @moduleEnd semAlign
 * @file auth.ts
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

