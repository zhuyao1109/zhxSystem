/**
 * 标准对齐 API 模块
 *
 * 与后端 mvp `/api/alignment/tasks` 系列接口对齐
 */

import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { buildCreateAlignmentTaskBody } from '@/api/alignmentPayload';
import type { ApiResponse } from '@/types';

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

export interface AlignmentChatResultData {
  answer: string;
  references: string[];
}

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
