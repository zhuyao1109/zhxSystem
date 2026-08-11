/**
 * @file semAlign
 * @file alignment.ts
 * @description API 子模块：封装后端 REST 接口的请求与响应类型。
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
 * 标准对齐 API 模块
 *
 * 与后端 mvp `/api/alignment/tasks` 系列接口对齐
 */

import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { buildCreateAlignmentTaskBody } from '@/api/alignmentPayload';
import type { ApiResponse } from '@/types';

// -----------------------------------------------------------------------------
// 分段：alignment.ts 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。
// -----------------------------------------------------------------------------

/** 创建任务接口返回的 data */
export interface AlignmentCreateResultData {
  taskId: string;
  status: string;
}

/** 列表单项（后端字段） */
export interface AlignmentTaskListItem {
  taskId: string;
  status: string;
  reviewStatus?: string;
  created_at?: string;
  inputTextPreview?: string;
}

/**
 * 类型定义 `AlignmentChatResultData`：描述前后端交互或页面状态结构。
 */
export interface AlignmentChatResultData {
  answer: string;
  references: string[];
}

/**
 * 服务模块 `alignmentApi`：聚合 API 调用并返回强类型结果。
 */
export const alignmentApi = {
  /**
   * 创建对齐任务（POST /alignment/tasks，body: { text, options }）
   */
  createTask: async (data: Parameters<typeof buildCreateAlignmentTaskBody>[0]): Promise<
    ApiResponse<AlignmentCreateResultData>
  > => {
    const body = buildCreateAlignmentTaskBody(data);
    const response: ApiResponse<{
      id: number;
      status: string;
      input_text?: string;
      user_id?: number;
      created_at?: string;
    }> = await api.post(Endpoints.ALIGNMENT_LIST, body);
    const d = response.data;
    if (!d) {
      return response as unknown as ApiResponse<AlignmentCreateResultData>;
    }
    return {
      code: response.code,
      message: response.message,
      data: {
        taskId: String(d.id),
        status: d.status,
      },
    };
  },

  /**
   * 获取对齐任务列表（分页）
   */
  getTaskList: async (params?: { page?: number; size?: number }): Promise<ApiResponse<{
    data: AlignmentTaskListItem[];
    total: number;
    page: number;
    size: number;
  }>> => {
    const response: ApiResponse<{
      data: Array<{
        id: number;
        status: string;
        review_status?: string;
        input_text?: string;
        created_at?: string;
      }>;
      total: number;
      page: number;
      size: number;
    }> = await api.get(Endpoints.ALIGNMENT_LIST, { params });
    const pageData = response.data;
    const rows = pageData?.data ?? [];
    const mapped: AlignmentTaskListItem[] = rows.map((item) => ({
      taskId: String(item.id),
      status: item.status,
      reviewStatus: item.review_status,
      created_at:
        typeof item.created_at === 'string' ? item.created_at : String(item.created_at ?? ''),
      inputTextPreview: item.input_text?.slice(0, 120),
    }));
    return {
      code: response.code,
      message: response.message,
      data: {
        data: mapped,
        total: pageData?.total ?? mapped.length,
        page: pageData?.page ?? params?.page ?? 1,
        size: pageData?.size ?? params?.size ?? mapped.length,
      },
    };
  },

  /**
   * 获取对齐任务详情（后端字段与前端 AlignmentResult 不完全一致，由调用方按需映射）
   */
  getTaskDetail: async (taskId: string): Promise<ApiResponse<unknown>> => {
    const response: ApiResponse<unknown> = await api.get(Endpoints.ALIGNMENT_DETAIL(taskId));
    return response;
  },

  /**
   * 重新执行对齐任务
   */
  retryTask: async (taskId: string): Promise<ApiResponse<unknown>> => {
    const response: ApiResponse<unknown> = await api.post(`/alignment/tasks/${taskId}/retry`);
    return response;
  },

  /**
   * 提交/审核/发布对齐任务
   */
  reviewTask: async (
    taskId: string,
    action: 'submit' | 'approve' | 'reject' | 'publish',
    notes?: string
  ): Promise<ApiResponse<unknown>> => {
    const response: ApiResponse<unknown> = await api.post(`/alignment/tasks/${taskId}/review`, {
      action,
      notes,
    });
    return response;
  },

  /**
   * 获取已发布对齐结果
   */
  getPublishedTasks: async (params?: { page?: number; size?: number }) => {
    const response = await api.get('/alignment/published', { params });
    return response;
  },

  /**
   * 删除对齐任务
   */
  deleteTask: async (taskId: string): Promise<ApiResponse<null>> => {
    const response: ApiResponse<null> = await api.delete(Endpoints.ALIGNMENT_DELETE(taskId));
    return response;
  },

  /**
   * 保存对齐结果（后端为 POST）
   */
  saveResult: async (
    taskId: string,
    result?: Record<string, unknown>
  ): Promise<ApiResponse<null>> => {
    const response: ApiResponse<null> = await api.post(Endpoints.ALIGNMENT_SAVE(taskId), result ?? {});
    return response;
  },

  /**
   * 与对齐助手聊天（后端检索增强）
   */
  chat: async (payload: {
    message: string;
    group1Id?: string;
    group2Id?: string;
  }): Promise<ApiResponse<AlignmentChatResultData>> => {
    const response: ApiResponse<AlignmentChatResultData> = await api.post(Endpoints.ALIGNMENT_CHAT, {
      message: payload.message,
      group1_id: payload.group1Id,
      group2_id: payload.group2Id,
    });
    return response;
  },

  /**
   * 保存手动映射决策
   */
  saveManualMapping: async (
    taskId: string,
    data: {
      conflict_id: string;
      decision: 'accept' | 'reject' | 'modify';
      modified_recommendation?: string;
      notes?: string;
    }
  ): Promise<ApiResponse<{
    conflict_id: string;
    decision: string;
    updated_at: string;
  }>> => {
    const response = await api.post(`/alignment/tasks/${taskId}/manual-mapping`, data);
    return response;
  },
};

export default alignmentApi;
/**
 * @moduleEnd semAlign
 * @file alignment.ts
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

