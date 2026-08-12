import apiAdapter from '@/api/adapter';
import type { WorkbenchData } from '@/types';

export interface WorkbenchServiceType {
  getDashboardData: () => Promise<WorkbenchData>;
  getMetrics: () => Promise<WorkbenchData['metrics']>;
  getCharts: () => Promise<WorkbenchData['charts']>;
  getDynamics: () => Promise<WorkbenchData['dynamics']>;
}

export const workbenchService: WorkbenchServiceType = {
  async getDashboardData(): Promise<WorkbenchData> {
    // 使用 API 适配器获取工作台数据
    const response = await apiAdapter.workbench.getDashboardData();
    return response.data;
  },

  async getMetrics() {
    const response = await apiAdapter.workbench.getDashboardData();
    return response.data.metrics;
  },

  async getCharts() {
    const response = await apiAdapter.workbench.getDashboardData();
    return response.data.charts;
  },

  async getDynamics() {
    const response = await apiAdapter.workbench.getDashboardData();
    return response.data.dynamics;
  },
};

export default workbenchService;
