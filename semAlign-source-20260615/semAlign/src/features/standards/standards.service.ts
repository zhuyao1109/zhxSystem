import apiAdapter from '@/api/adapter';
import type { Standard, PaginatedResponse } from '@/types';

export interface StandardsQueryParams {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
  department?: string;
  category?: string;
}

export interface StandardsServiceType {
  getList: (params?: StandardsQueryParams) => Promise<PaginatedResponse<Standard>>;
  getById: (id: string) => Promise<Standard>;
  create: (data: Omit<Standard, 'id'>) => Promise<Standard>;
  update: (id: string, data: Partial<Standard>) => Promise<Standard>;
  delete: (id: string) => Promise<void>;
}

export const standardsService: StandardsServiceType = {
  async getList(params?: StandardsQueryParams): Promise<PaginatedResponse<Standard>> {
    const response = await apiAdapter.standards.getList(params);
    return response.data;
  },

  async getById(id: string): Promise<Standard> {
    const response = await apiAdapter.standards.getById(id);
    return response.data;
  },

  async create(data: Omit<Standard, 'id'>): Promise<Standard> {
    const response = await apiAdapter.standards.create(data);
    return response.data;
  },

  async update(id: string, data: Partial<Standard>): Promise<Standard> {
    const response = await apiAdapter.standards.update(id, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await apiAdapter.standards.delete(id);
  },
};

export default standardsService;
