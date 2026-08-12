/**
 * 对齐服务
 */

import { alignmentApi } from '@/api/modules/alignment';

export const alignmentService = {
  /**
   * 创建对齐任务
   */
  createTask: async (data: {
    group1Id: string;
    group2Id: string;
    group1Name?: string;
    group2Name?: string;
    priorityRules: string[];
    customRule?: string;
  }) => {
    return await alignmentApi.createTask(data);
  },

  /**
   * 获取对齐任务列表
   */
  getTaskList: async (params?: { page?: number; size?: number }) => {
    return await alignmentApi.getTaskList(params);
  },

  /**
   * 获取对齐任务详情
   */
  getTaskDetail: async (taskId: string) => {
    return await alignmentApi.getTaskDetail(taskId);
  },

  /**
   * 重新执行对齐任务
   */
  retryTask: async (taskId: string) => {
    return await alignmentApi.retryTask(taskId);
  },

  /**
   * 删除对齐任务
   */
  deleteTask: async (taskId: string) => {
    return await alignmentApi.deleteTask(taskId);
  },

  /**
   * 保存对齐结果
   */
  saveResult: async (taskId: string, result: any) => {
    return await alignmentApi.saveResult(taskId, result);
  },

  /**
   * 对齐助手聊天
   */
  chat: async (data: { message: string; group1Id?: string; group2Id?: string }) => {
    return await alignmentApi.chat(data);
  },
};

export default alignmentService;
