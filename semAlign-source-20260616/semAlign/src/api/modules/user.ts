/**
 * 用户管理 API
 */
import api from '../axios';
import { Endpoints } from '../endpoints';
import type { ApiResponse } from '@/types';

export interface UserProfile {
  id: number;
  username: string;
  email?: string;
  role: string;
  is_active: boolean;
  avatar?: string;
  created_at: string;
}

export interface UpdateProfileRequest {
  email?: string;
  avatar?: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

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
