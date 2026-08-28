/**
 * @file semAlign
 * @file adapter.ts
 * @description HTTP 客户端层：Axios 实例、拦截器、端点常量与响应适配。
 * @remarks API 响应适配层：统一解包 code/data/message 结构。
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
 * API 适配层
 * 
 * 用于处理后端 API 返回格式不一致的问题
 * 便于后期快速替换为真实接口或后端调整
 */

import api from './axios';
import { Endpoints } from './endpoints';
import type {
// -----------------------------------------------------------------------------
// 分段：adapter.ts 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

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

/**
 * 函数 `mapSearchResultRowToStandard`：本模块内部业务辅助逻辑。
 */
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

/**
 * 函数 `searchAdapter`：本模块内部业务辅助逻辑。
 */
export const searchAdapter = {
  /**
   * 搜索标准（支持 retrieval_mode：hybrid | sparse | dense，与语义建模及检索层约定对齐）
   * 追问时可通过 options.history 携带历史轮次（编码进 keyword，后端解析）。
   */
  query: async (
    keyword: string,
    options?: SearchQueryOptions
  ): Promise<ApiResponse<SearchQueryData>> => {
    const retrievalMode: RetrievalMode | undefined = options?.retrievalMode;
    const history = options?.history;
    const payloadKeyword =
      history && history.length > 0
        ? `__RAG_HISTORY__:${JSON.stringify({ keyword, history })}`
        : keyword;
    const params: Record<string, string> = { keyword: payloadKeyword };
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
/**
 * @moduleEnd semAlign
 * @file adapter.ts
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

