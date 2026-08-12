import type {
  WorkbenchData,
  Metric,
  Dynamic,
  PaginatedResponse,
  Standard,
  SearchSuggestion,
  ImportTask,
  UploadDataItem,
} from '@/types';
import {
  MOCK_METRICS,
  MOCK_DYNAMICS,
  MOCK_STANDARDS,
  SYSTEM_MATRIX_DATA,
  LIFECYCLE_PIE_DATA,
  PROCESS_EFFICIENCY_DATA,
  LIFECYCLE_COMPARISON_DATA,
  SEARCH_SUGGESTIONS,
} from '@/constants';

const delay = (ms?: number) => {
  const delayMs = ms ?? Math.floor(Math.random() * 500) + 300;
  return new Promise((resolve) => setTimeout(resolve, delayMs));
};

const simulateError = (errorRate = 0.02): boolean => {
  return Math.random() < errorRate;
};

function paginate<T>(items: T[], params: { page?: number; size?: number }): PaginatedResponse<T> {
  const page = params.page || 1;
  const size = params.size || 10;
  const start = (page - 1) * size;
  const end = start + size;

  return {
    data: items.slice(start, end),
    total: items.length,
    page,
    size,
  };
}

function searchItems<T extends Record<string, any>>(items: T[], keyword: string, fields: (keyof T)[]): T[] {
  if (!keyword) return items;
  const lowerKeyword = keyword.toLowerCase();
  return items.filter((item) => fields.some((field) => String(item[field]).toLowerCase().includes(lowerKeyword)));
}

export const mockApi = {
  workbench: {
    getDashboardData: async (): Promise<WorkbenchData> => {
      await delay(400);
      if (simulateError()) throw new Error('获取工作台数据失败');

      return {
        metrics: MOCK_METRICS,
        charts: {
          distribution: [
            { name: '基础通用', value: 35 },
            { name: '业务标准', value: 45 },
            { name: '管理标准', value: 20 },
          ],
          trend: [
            { name: '1月', value: 120 },
            { name: '2月', value: 145 },
            { name: '3月', value: 138 },
            { name: '4月', value: 156 },
          ],
          comparison: [
            { name: '机务', value: 85 },
            { name: '运营', value: 92 },
            { name: '安全', value: 78 },
          ],
          lifecycle: LIFECYCLE_PIE_DATA,
          category: SYSTEM_MATRIX_DATA.map((item) => ({ name: item.title, value: item.count })),
          efficiency: PROCESS_EFFICIENCY_DATA,
          stage_distribution: LIFECYCLE_COMPARISON_DATA,
          efficiency_kpis: {
            avg_review_days: 7.2,
            avg_publish_days: 15.8,
            review_mom_delta: -0.3,
            publish_mom_delta: 0.2,
          },
        },
        dynamics: MOCK_DYNAMICS,
      };
    },

    getMetrics: async (): Promise<Metric[]> => {
      await delay();
      if (simulateError()) throw new Error('获取指标数据失败');
      return MOCK_METRICS;
    },

    getDynamics: async (): Promise<Dynamic[]> => {
      await delay();
      if (simulateError()) throw new Error('获取动态失败');
      return MOCK_DYNAMICS;
    },
  },

  standards: {
    getList: async (params?: {
      page?: number;
      size?: number;
      keyword?: string;
      status?: string;
      department?: string;
      category?: string;
    }): Promise<PaginatedResponse<Standard>> => {
      await delay(400);
      if (simulateError()) throw new Error('获取标准列表失败');

      let result = [...MOCK_STANDARDS];

      if (params?.keyword) {
        result = searchItems(result, params.keyword, ['name', 'code', 'description']);
      }

      if (params?.status) {
        result = result.filter((s) => s.status === params.status);
      }

      if (params?.department) {
        result = result.filter((s) => s.department === params.department);
      }

      if (params?.category) {
        result = result.filter((s) => s.category === params.category);
      }

      return paginate(result, params || {});
    },

    getById: async (id: string): Promise<Standard> => {
      await delay(300);
      if (simulateError()) throw new Error('获取标准详情失败');

      const item = MOCK_STANDARDS.find((s) => s.id === id);
      if (!item) throw new Error('标准不存在');
      return item;
    },

    create: async (data: Omit<Standard, 'id'>): Promise<Standard> => {
      await delay(600);
      if (simulateError()) throw new Error('创建标准失败');

      return {
        ...data,
        id: Date.now().toString(),
      };
    },

    update: async (id: string, data: Partial<Standard>): Promise<Standard> => {
      await delay(500);
      if (simulateError()) throw new Error('更新标准失败');

      const item = MOCK_STANDARDS.find((s) => s.id === id);
      if (!item) throw new Error('标准不存在');

      return { ...item, ...data };
    },

    delete: async (id: string): Promise<void> => {
      await delay(400);
      if (simulateError()) throw new Error('删除标准失败');
    },
  },

  search: {
    query: async (keyword: string): Promise<{ standards: Standard[]; suggestions: SearchSuggestion[]; total: number }> => {
      await delay(500);
      if (simulateError()) throw new Error('搜索失败');

      const standards = searchItems(MOCK_STANDARDS, keyword, ['name', 'code', 'description']);

      const suggestions: SearchSuggestion[] = [
        { type: 'popular', text: `${keyword} 标准`, count: Math.floor(Math.random() * 1000) },
        { type: 'popular', text: `${keyword} 规范`, count: Math.floor(Math.random() * 500) },
        ...SEARCH_SUGGESTIONS.slice(0, 3),
      ];

      return {
        standards,
        suggestions,
        total: standards.length,
      };
    },

    getSuggestions: async (keyword: string): Promise<SearchSuggestion[]> => {
      await delay(200);
      if (!keyword) return SEARCH_SUGGESTIONS;

      return SEARCH_SUGGESTIONS.filter((s) => s.text.toLowerCase().includes(keyword.toLowerCase()));
    },
  },

  import: {
    upload: async (file: File): Promise<ImportTask> => {
      await delay(1000);
      if (simulateError()) throw new Error('文件上传失败');

      return {
        taskId: `import-${Date.now()}`,
        status: 'processing',
        progress: 0,
        fileName: file.name,
      };
    },

    getStatus: async (taskId: string): Promise<ImportTask> => {
      await delay(300);

      const progress = Math.floor(Math.random() * 100);
      const status = progress >= 100 ? 'completed' : 'processing';

      return {
        taskId,
        status,
        progress,
        result:
          status === 'completed'
            ? {
                total: 100,
                success: 98,
                failed: 2,
              }
            : undefined,
      };
    },

    uploadFile: async (file: File) => {
      await delay(800);
      if (simulateError()) throw new Error('文件上传失败');

      // 模拟解析结果
      const mockData = [
        { standard_no: 'GB/T 2023-4.1', name: '航空运输包装标准', version: 'V2.1', status: '有效', validation_status: 'valid' as const },
        { standard_no: 'MH/T 5012-3', name: '机场地面服务规范', version: 'V1.3', status: '有效', validation_status: 'valid' as const },
        { standard_no: 'GB/T 3966-2024', name: '危险品运输标准', version: 'V3.0', status: '审核中', validation_status: 'needs_update' as const },
        { standard_no: 'MH/T 3021-2', name: '航材管理规范', version: 'V1.1', status: '草稿', validation_status: 'duplicate' as const },
        { standard_no: 'GB/T 4058-4', name: '航空餐饮服务标准', version: 'V2.0', status: '有效', validation_status: 'valid' as const },
      ];

      return {
        data: {
          filename: file.name,
          status: 'success' as const,
          validation: {
            total_rows: mockData.length,
            valid_rows: mockData.filter(d => d.validation_status === 'valid').length,
            need_update: mockData.filter(d => d.validation_status === 'needs_update').length,
            duplicate_rows: mockData.filter(d => d.validation_status === 'duplicate').length,
            data: mockData,
          },
          message: '文件解析成功',
        },
        file,
      };
    },

    importRecords: async (_records: UploadDataItem[]) => {
      await delay(500);
      if (simulateError()) throw new Error('导入失败');

      return {
        status: 'success' as const,
        message: '导入成功',
        imported: 3,
        updated: 1,
        conflicts: 0,
      };
    },
  },
};

export default mockApi;
