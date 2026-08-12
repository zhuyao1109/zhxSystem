import { useState, useCallback } from 'react';
import { useToast } from '@/components/common';
import { importApi } from './import.service';
import { getApiErrorMessage } from '@/utils/apiError';
import type { UploadResponse, ImportResponse, UploadDataItem, ImportStatus } from '@/types';

interface UseImportReturn {
  status: ImportStatus;
  file: File | null;
  parseResult: UploadResponse['validation'] | null;
  importResult: ImportResponse | null;
  error: string | null;
  successMessage: string;
  uploadFile: (file: File) => Promise<void>;
  submitImport: () => Promise<void>;
  reset: () => void;
}

export const useImport = (): UseImportReturn => {
  const [status, setStatus] = useState<ImportStatus>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [parseResult, setParseResult] = useState<UploadResponse['validation'] | null>(null);
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedData, setUploadedData] = useState<UploadDataItem[]>([]);
  const [successMessage, setSuccessMessage] = useState<string>('');

  const { showSuccess, showError } = useToast();

  const uploadFile = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setStatus('parsing');
    setError(null);
    setParseResult(null);
    setImportResult(null);

    try {
      const response = await importApi.uploadFile(selectedFile);

      setParseResult(response.validation);
      setUploadedData(response.validation.data);
      setStatus('success');
      setSuccessMessage(response.message);

      // 显示 toast 消息
      showSuccess(response.message);
    } catch (err) {
      const errorMessage = getApiErrorMessage(err, '文件解析失败，请检查文件格式');
      setError(errorMessage);
      setStatus('error');
      showError(errorMessage);
    }
  }, [showSuccess, showError]);

  const submitImport = useCallback(async () => {
    if (!uploadedData.length) {
      showError('没有可导入的数据');
      return;
    }

    try {
      const result = await importApi.importRecords(uploadedData);
      setImportResult(result);

      // 直接使用 API 返回的消息
      showSuccess(result.message);
    } catch (err) {
      const errorMessage = getApiErrorMessage(err, '导入失败，请重试');
      showError(errorMessage);
    }
  }, [uploadedData, showError, showSuccess]);

  const reset = useCallback(() => {
    setStatus('idle');
    setFile(null);
    setParseResult(null);
    setImportResult(null);
    setError(null);
    setUploadedData([]);
    setSuccessMessage('');
  }, []);

  return {
    status,
    file,
    parseResult,
    importResult,
    error,
    successMessage,
    uploadFile,
    submitImport,
    reset,
  };
};
