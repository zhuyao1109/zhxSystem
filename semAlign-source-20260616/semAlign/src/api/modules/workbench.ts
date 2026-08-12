import api from '../axios';
import { Endpoints } from '../endpoints';
import type { ApiResponse, WorkbenchData, Metric, Dynamic } from '@/types';

export const workbenchApi = {
  /**
   * 获取工作台数据（GET /workbench/dashboard，一次返回 metrics + charts + dynamics）
   */
  getDashboardData: async (): Promise<ApiResponse<WorkbenchData>> => {
    return api.get(Endpoints.DASHBOARD);
  },

  /**
   * 指标数据（后端无独立路由，由 dashboard 聚合结果拆分）
   */
  getMetrics: async (): Promise<ApiResponse<Metric[]>> => {
    const full: ApiResponse<WorkbenchData> = await api.get(Endpoints.DASHBOARD);
    return {
      code: full.code,
      message: full.message,
      data: full.data?.metrics ?? [],
    };
  },

  /**
   * 动态列表（后端无独立路由，由 dashboard 聚合结果拆分）
   */
  getDynamics: async (): Promise<ApiResponse<Dynamic[]>> => {
    const full: ApiResponse<WorkbenchData> = await api.get(Endpoints.DASHBOARD);
    return {
      code: full.code,
      message: full.message,
      data: full.data?.dynamics ?? [],
    };
  },
};

export default workbenchApi;
