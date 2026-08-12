import apiAdapter from '@/api/adapter';
import type { UploadResponse, ImportResponse, UploadDataItem } from '@/types';

export const importApi = {
  uploadFile: async (file: File): Promise<UploadResponse> => {
    return apiAdapter.import.uploadFile(file);
  },

  importRecords: async (records: UploadDataItem[]): Promise<ImportResponse> => {
    return apiAdapter.import.importRecords(records);
  },
};

export default importApi;