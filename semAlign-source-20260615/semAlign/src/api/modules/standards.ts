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

export interface StandardsQueryParams {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
  department?: string;
  category?: string;
}

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