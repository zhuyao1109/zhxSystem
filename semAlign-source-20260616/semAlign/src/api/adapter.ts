/**
 * API 适配层
 * 
 * 用于处理后端 API 返回格式不一致的问题
 * 便于后期快速替换为真实接口或后端调整
 */

import api from './axios';
import { Endpoints } from './endpoints';
import type {
  ApiResponse,
  PaginatedResponse,
  Standard,
  UploadResponse,
  ImportResponse,
  UploadDataItem,
  WorkbenchData,
  SearchSuggestion,
  SearchQueryData,
  SearchQueryOptions,
  RetrievalMode,
} from '@/types';
import {
  mapStandardFromBackend,
  mapStandardsFromBackend,
  mapWorkbenchFromBackend,
  mapStandardToBackend,
} from '@/utils/dataMapper';
import { buildCreateAlignmentTaskBody } from '@/api/alignmentPayload';

/** semAlign_backend GET /search 返回 data.results 中单条形状 */
interface BackendSearchResultRow {
  id: number;
  standard_no: string;
  name: string;
  version: string;
  status: string;
  category: string;
  department?: string | null;
  source_file?: string | null;
  match_excerpt?: string | null;
  relevance_score?: number;
}

/** 将后端相关度统一为 0–100，供列表「语义相关度」条使用 */
function normalizeRelevanceScore(raw: number | undefined): number | undefined {
  if (raw == null || Number.isNaN(raw)) {
    return undefined;
  }
  if (raw >= 0 && raw <= 1) {
    return Math.round(raw * 100);
  }
  return Math.min(100, Math.max(0, Math.round(raw)));
}

function mapSearchResultRowToStandard(r: BackendSearchResultRow): Standard {
  const statusMap: Record<string, Standard['status']> = {
    有效: 'active',
    草稿: 'draft',
    审核中: 'review',
    已废止: 'deprecated',
    新增: 'new',
  };
  return {
    id: String(r.id),
    code: r.standard_no,
    name: r.name,
    version: r.version,
    status: statusMap[r.status] || (r.status as Standard['status']),
    department: r.department || r.source_file || '',
    date: new Date().toISOString().slice(0, 10),
    category: r.category || '',
    description: r.match_excerpt || undefined,
    relevanceScore: normalizeRelevanceScore(r.relevance_score),
  };
}

// ==================== 标准管理适配器 ====================

export const standardsAdapter = {
  /**
   * 获取标准列表（适配后端返回格式）
   */
  getList: async (params?: {
    page?: number;
    size?: number;
    keyword?: string;
    status?: string;
    department?: string;
    category?: string;
  }): Promise<ApiResponse<PaginatedResponse<Standard>>> => {
    const { keyword, status, department, ...rest } = params ?? {};
    const queryParams = {
      ...rest,
      ...(status !== undefined && status !== '' ? { status } : {}),
      ...(department !== undefined && department !== '' ? { department } : {}),
      ...(keyword !== undefined && keyword !== '' ? { search: keyword } : {}),
    };
    const response: any = await api.get(Endpoints.STANDARDS, { params: queryParams });
    
    // 后端返回格式：{ code, message, data: { data: [], total, page, size } }
    const backendData = response.data;
    
    return {
      code: response.code,
      message: response.message,
      data: {
        data: mapStandardsFromBackend(backendData.data || []),
        total: backendData.total || 0,
        page: backendData.page || 1,
        size: backendData.size || 10,
      },
    };
  },

  /**
   * 获取标准详情（适配后端返回格式）
   */
  getById: async (id: string): Promise<ApiResponse<Standard>> => {
    const response: any = await api.get(Endpoints.STANDARD_DETAIL(id));
    
    return {
      code: response.code,
      message: response.message,
      data: mapStandardFromBackend(response.data),
    };
  },

  /**
   * 创建标准（映射字段名）
   */
  create: async (data: Omit<Standard, 'id'>): Promise<ApiResponse<Standard>> => {
    // 前端数据 -> 后端数据
    const backendData = mapStandardToBackend(data);
    
    // 使用 POST /import 接口（支持批量）
    const response: any = await api.post(Endpoints.IMPORT, [backendData]);
    
    return {
      code: response.code,
      message: response.message,
      data: mapStandardFromBackend(response.data[0]),
    };
  },

  /**
   * 更新标准（映射字段名）
   */
  update: async (id: string, data: Partial<Standard>): Promise<ApiResponse<Standard>> => {
    const backendData = mapStandardToBackend(data);
    
    const response: any = await api.put(Endpoints.STANDARD_UPDATE(id), backendData);
    
    return {
      code: response.code,
      message: response.message,
      data: mapStandardFromBackend(response.data),
    };
  },

  /**
   * 删除标准
   */
  delete: async (id: string): Promise<ApiResponse<null>> => {
    const response: any = await api.delete(Endpoints.STANDARD_DELETE(id));
    
    return {
      code: response.code,
      message: response.message,
      data: null,
    };
  },
};

// ==================== 工作台适配器 ====================

export const workbenchAdapter = {
  /**
   * 获取工作台数据（适配 Metric 字段）
   */
  getDashboardData: async (): Promise<ApiResponse<WorkbenchData>> => {
    const response: any = await api.get(Endpoints.DASHBOARD);
    
    // 映射工作台数据
    const workbenchData = mapWorkbenchFromBackend(response.data);
    
    return {
      code: response.code,
      message: response.message,
      data: workbenchData,
    };
  },
};

// ==================== 搜索适配器 ====================

function parseReasoningSteps(reasoningRaw: unknown): string[] | undefined {
  if (Array.isArray(reasoningRaw)) {
    return reasoningRaw.map((s: unknown) => String(s));
  }
  if (typeof reasoningRaw === 'string' && reasoningRaw.trim()) {
    return [reasoningRaw.trim()];
  }
  return undefined;
}

export const searchAdapter = {
  /**
   * 搜索标准（支持 retrieval_mode：hybrid | sparse | dense，与语义建模及检索层约定对齐）
   */
  query: async (
    keyword: string,
    options?: SearchQueryOptions
  ): Promise<ApiResponse<SearchQueryData>> => {
    const retrievalMode: RetrievalMode | undefined = options?.retrievalMode;
    const params: Record<string, string> = { keyword };
    if (retrievalMode) {
      params.retrieval_mode = retrievalMode;
    }

    const response: any = await api.get(Endpoints.SEARCH, { params });

    const rows: BackendSearchResultRow[] = response.data?.results ?? response.data?.standards ?? [];
    const reasoningRaw = response.data?.reasoning_steps ?? response.data?.reasoning;
    const reasoning_steps = parseReasoningSteps(reasoningRaw);

    return {
      code: response.code,
      message: response.message,
      data: {
        standards: rows.map(mapSearchResultRowToStandard),
        suggestions: response.data?.suggestions || [],
        total: response.data?.total ?? rows.length,
        answer: response.data?.answer ?? '',
        sources: response.data?.sources ?? [],
        reasoning_steps,
      },
    };
  },

  /**
   * 获取搜索建议（后端 keyword 必填，无关键词时不请求）
   */
  getSuggestions: async (keyword?: string): Promise<ApiResponse<SearchSuggestion[]>> => {
    const k = keyword?.trim();
    if (!k) {
      return { code: 200, message: 'success', data: [] };
    }
    const response: { code: number; message: string; data?: SearchSuggestion[] } = await api.get(
      Endpoints.SEARCH_SUGGEST,
      { params: { keyword: k } }
    );

    return {
      code: response.code,
      message: response.message,
      data: response.data ?? [],
    };
  },
};

// ==================== 导入适配器 ====================

export const importAdapter = {
  /**
   * 上传文件（特殊处理：后端返回格式不统一）
   */
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    // 直接使用 axios.post，跳过响应拦截器
    // 实例默认带 application/json；上传时必须去掉 Content-Type，让浏览器为 FormData 生成 boundary
    const response: {
      code: number;
      message: string;
      data: UploadResponse;
    } = await api.post(Endpoints.UPLOAD, formData, {
      timeout: 180000,
      transformRequest: [
        (data, headers) => {
          if (data instanceof FormData) {
            delete (headers as Record<string, string>)['Content-Type'];
          }
          return data as FormData;
        },
      ],
    });

    if (response.code !== 200 || !response.data) {
      throw new Error(response.message || '上传失败');
    }
    return response.data;
  },

  /**
   * 提交导入 — POST /import/records，响应 ImportResponse
   */
  importRecords: async (records: UploadDataItem[]): Promise<ImportResponse> => {
    const backendRecords = records.map((record) => ({
      standard_no: record.standard_no,
      name: record.name,
      version: record.version,
      status: record.status,
      category: (record as UploadDataItem & { category?: string }).category,
      department: (record as UploadDataItem & { department?: string }).department,
      description: (record as UploadDataItem & { description?: string }).description,
      source_file: (record as UploadDataItem & { source_file?: string }).source_file,
      saved_filename: (record as UploadDataItem & { saved_filename?: string }).saved_filename,
      validation_status: record.validation_status,
      validation_error: (record as UploadDataItem & { validation_error?: string }).validation_error,
      conflict_status: record.conflict_status,
      rule_violations: record.rule_violations,
    }));

    const response: {
      code: number;
      message: string;
      data: {
        imported_count: number;
        updated_count?: number;
        failed_count: number;
        errors: string[];
      };
    } = await api.post(Endpoints.IMPORT_RECORDS, backendRecords);

    if (response.code !== 200 || !response.data) {
      return {
        status: 'error',
        message: response.message || '导入失败',
        imported: 0,
        updated: 0,
        conflicts: 0,
      };
    }

    const d = response.data;
    return {
      status: d.failed_count > 0 && d.imported_count + (d.updated_count ?? 0) === 0 ? 'error' : 'success',
      message: response.message || '导入完成',
      imported: d.imported_count,
      updated: d.updated_count ?? 0,
      conflicts: d.failed_count,
    };
  },
};

// ==================== 对齐适配器 ====================

export const alignmentAdapter = {
  /**
   * 创建对齐任务
   */
  createTask: async (data: {
    group1Id: string;
    group2Id: string;
    priorityRules: string[];
    customRule?: string;
  }): Promise<ApiResponse<{ taskId: string; status: string }>> => {
    const body = buildCreateAlignmentTaskBody(data);
    const response: {
      code: number;
      message: string;
      data?: { id: number; status: string };
    } = await api.post(Endpoints.ALIGNMENT_LIST, body);
    const d = response.data;
    if (!d) {
      return response as unknown as ApiResponse<{ taskId: string; status: string }>;
    }
    return {
      code: response.code,
      message: response.message,
      data: { taskId: String(d.id), status: d.status },
    };
  },

  /**
   * 获取对齐任务列表
   */
  getTaskList: async (): Promise<ApiResponse<{ taskId: string; status: string }[]>> => {
    const response: {
      code: number;
      message: string;
      data?: { data: Array<{ id: number; status: string }> };
    } = await api.get(Endpoints.ALIGNMENT_LIST);
    const page = response.data;
    const rows = page?.data ?? [];
    return {
      code: response.code,
      message: response.message,
      data: rows.map((item) => ({ taskId: String(item.id), status: item.status })),
    };
  },

  /**
   * 获取对齐任务详情
   */
  getTaskDetail: async (taskId: string): Promise<ApiResponse<any>> => {
    const response: any = await api.get(Endpoints.ALIGNMENT_DETAIL(taskId));
    return response;
  },

  /**
   * 删除对齐任务
   */
  deleteTask: async (taskId: string): Promise<ApiResponse<null>> => {
    const response: any = await api.delete(Endpoints.ALIGNMENT_DELETE(taskId));
    return response;
  },

  /**
   * 保存对齐结果
   */
  saveResult: async (taskId: string, result: any): Promise<ApiResponse<null>> => {
    const response: any = await api.post(Endpoints.ALIGNMENT_SAVE(taskId), result ?? {});
    return response;
  },
};

// ==================== 统一导出 ====================

/**
 * API 适配器统一导出
 * 使用此适配器可以确保与后端接口的兼容性
 */
export const apiAdapter = {
  standards: standardsAdapter,
  workbench: workbenchAdapter,
  search: searchAdapter,
  import: importAdapter,
  alignment: alignmentAdapter,
};

export default apiAdapter;
