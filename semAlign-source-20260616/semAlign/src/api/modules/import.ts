/**
 * 标准导入 API 模块
 * 
 * 提供文件上传和批量导入功能
 */

import apiAdapter from '@/api/adapter';
import type {
  UploadResponse,
  ImportResponse,
  UploadDataItem,
} from '@/types';

export const importApi = {
  /**
   * 上传文件并解析
   */
  uploadFile: async (file: File): Promise<UploadResponse> => {
    return apiAdapter.import.uploadFile(file);
  },

  /**
   * 提交导入记录
   */
  importRecords: async (records: UploadDataItem[]): Promise<ImportResponse> => {
    return apiAdapter.import.importRecords(records);
  },
};

export default importApi;