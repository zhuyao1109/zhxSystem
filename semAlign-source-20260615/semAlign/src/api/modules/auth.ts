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

function mapBackendRole(role: string): User['role'] {
  if (role === 'admin') {
    return 'admin';
  }
  if (role === 'user') {
    return 'user';
  }
  return 'viewer';
}

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

function failResponse<T>(raw: ApiResponse<BackendLoginData>): ApiResponse<T> {
  return { code: raw.code, message: raw.message };
}

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
