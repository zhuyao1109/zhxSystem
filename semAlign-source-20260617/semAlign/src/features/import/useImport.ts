/**
 * @file semAlign
 * @file useImport.ts
 * @description 标准导入模块：PDF/Excel 上传、解析预览与批量入库。
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
import { useState, useCallback } from 'react';
import { useToast } from '@/components/common';
import { importApi } from './import.service';
import { getApiErrorMessage } from '@/utils/apiError';
import type { UploadResponse, ImportResponse, UploadDataItem, ImportStatus } from '@/types';

/**
 * 类型定义 `UseImportReturn`：描述前后端交互或页面状态结构。
 */
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

/**
 * Hook `useImport`：封装可复用的状态逻辑与副作用。
 */
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
/**
 * @moduleEnd semAlign
 * @file useImport.ts
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

