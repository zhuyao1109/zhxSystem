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
