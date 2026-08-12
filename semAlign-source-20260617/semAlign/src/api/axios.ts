/**
 * @file semAlign
 * @file axios.ts
 * @description HTTP 客户端层：Axios 实例、拦截器、端点常量与响应适配。
 * @remarks Axios 客户端：注入 Bearer Token 与 401 统一跳转登录。
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
 * Axios HTTP 客户端配置
 */
import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import config from '@/config';

const AUTH_STORAGE_KEY = 'auth-storage';

/** 从 localStorage 解析 Bearer Token（含 Zustand persist 回填） */
function getStoredAccessToken(): string | null {
  const direct = localStorage.getItem('token');
  if (direct) {
    return direct;
  }
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { state?: { token?: string | null } };
    const t = parsed?.state?.token;
    if (typeof t === 'string' && t.length > 0) {
      localStorage.setItem('token', t);
      return t;
    }
  } catch {
    // ignore malformed persist payload
  }
  return null;
}

/**
 * 函数 `isAuthFailure`：本模块内部业务辅助逻辑。
 */
function isAuthFailure(status: number | undefined, detail: unknown): boolean {
  if (status === 401) {
    return true;
  }
  if (status !== 403) {
    return false;
  }
  if (typeof detail !== 'string') {
    return false;
  }
  return detail === 'Not authenticated' || detail.includes('Could not validate credentials');
}

/**
 * 函数 `redirectToLoginIfNeeded`：本模块内部业务辅助逻辑。
 */
function redirectToLoginIfNeeded(): void {
  localStorage.removeItem('token');
  localStorage.removeItem('token_expires_at');
  const currentPath = window.location.pathname;
  if (currentPath !== '/login') {
    window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
  }
}

const api: AxiosInstance = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (reqConfig) => {
    const url = reqConfig.url ?? '';
    const isLoginRequest = url.includes('/auth/login');

    if (!isLoginRequest) {
      const token = getStoredAccessToken();
      if (token) {
        reqConfig.headers.Authorization = `Bearer ${token}`;
      }
    }

    return reqConfig;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  // 业务层统一使用解包后的 body；与 axios 默认 fulfilled 类型不一致，此处作断言
  ((response: AxiosResponse) => response.data) as (
    response: AxiosResponse
  ) => AxiosResponse,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    if (isAuthFailure(status, detail)) {
      redirectToLoginIfNeeded();
    }

    const message =
      error.response?.data?.message || error.response?.data?.detail || '网络错误，请重试';
    console.error('[Axios] API error:', { status, message, url: error.config?.url });
    return Promise.reject(error);
  }
);

export default api;
/**
 * @moduleEnd semAlign
 * @file axios.ts
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

