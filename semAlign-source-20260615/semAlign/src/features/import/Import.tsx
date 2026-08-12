import React, { useState, useCallback } from 'react';
import { Upload, FileSpreadsheet, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { SectionTitle } from '@/components/common';
import { Card, Button, Badge } from '@/components/ui';
import { useImport } from './useImport';
import type { UploadDataItem } from '@/types';

const getStatusBadge = (validationStatus: string) => {
  switch (validationStatus) {
    case 'valid':
      return { label: '有效', status: 'active' as const };
    case 'invalid':
      return { label: '无效', status: 'deprecated' as const };
    case 'duplicate':
      return { label: '重复', status: 'review' as const };
    case 'needs_update':
      return { label: '待更新', status: 'new' as const };
    default:
      return { label: validationStatus, status: 'draft' as const };
  }
};

const Import: React.FC = () => {
  const { status, file, parseResult, successMessage, error: uploadError, uploadFile, submitImport, reset } =
    useImport();
  const [dragActive, setDragActive] = useState<boolean>(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const selectedFile = e.dataTransfer.files[0];
        const validTypes = ['.xlsx', '.xls', '.pdf'];
        const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
        if (!validTypes.includes(ext)) {
          alert('不支持的文件格式，请上传 xlsx、xls 或 pdf 文件');
          return;
        }
        if (selectedFile.size > 20 * 1024 * 1024) {
          alert('文件大小不能超过 20MB');
          return;
        }
        uploadFile(selectedFile);
      }
    },
    [uploadFile]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
        const selectedFile = e.target.files[0];
        if (selectedFile.size > 20 * 1024 * 1024) {
          alert('文件大小不能超过 20MB');
          return;
        }
        uploadFile(selectedFile);
      }
    },
    [uploadFile]
  );

  const handleSubmit = useCallback(() => {
    submitImport();
  }, [submitImport]);

  const displayData = parseResult?.data ?? [];
  const hasValidData = displayData.length > 0;
  const canSubmitImport = status === 'success' && hasValidData;

  return (
    <div>
      <SectionTitle
        title="标准导入"
        subtitle="支持Excel文件批量导入或手动录入标准信息，系统将自动验证数据完整性并检测重复"
      />

      <Card className="mb-8">
        <div
          className={`
            border-2 border-dashed rounded-lg p-12 flex flex-col items-center justify-center transition-colors
            ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50'}
            ${status === 'success' ? 'bg-green-50 border-green-200' : ''}
            ${status === 'error' ? 'bg-red-50 border-red-200' : ''}
          `}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {status === 'idle' && (
            <>
              <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Upload className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-lg font-medium text-slate-800 mb-2">拖拽文件到此处或点击上传</h3>
              <p className="text-slate-500 text-sm mb-6">支持 xlsx/xls/pdf 格式文件，大小不超过 20MB</p>
              <div className="relative inline-block">
                <Button className="!text-white">选择文件</Button>
                <input
                  type="file"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  accept=".xlsx,.xls,.pdf"
                  onChange={handleFileChange}
                />
              </div>
            </>
          )}

          {status === 'parsing' && (
            <div className="flex flex-col items-center">
              <Loader2 className="h-12 w-12 text-amber-500 animate-spin mb-4" />
              <p className="text-amber-600 font-medium">文件正在解析中，请稍候...</p>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center">
              <CheckCircle2 className="h-12 w-12 text-green-500 mb-4" />
              <p className="text-green-700 font-medium">文件解析完成，标准库已更新</p>
              {file && <p className="text-green-600 text-sm mt-1">{file.name}</p>}
              <Button variant="ghost" className="mt-4 text-green-700 hover:bg-green-100" onClick={reset}>
                重新上传
              </Button>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-col items-center max-w-lg mx-auto px-2">
              <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
              <p className="text-red-700 font-medium">文件解析失败</p>
              {file ? (
                <p className="text-red-600 text-sm mt-2 text-center break-all">
                  上传文件：{file.name}
                </p>
              ) : null}
              {uploadError ? (
                <p className="text-red-600 text-sm mt-3 text-center leading-relaxed whitespace-pre-wrap">
                  {uploadError}
                </p>
              ) : null}
              <p className="text-red-500/90 text-xs mt-3 text-center leading-relaxed">
                请上传包含标准编号的文档，例如：GB/T、MH/T、ISO（如 GB/T 39445-2020）。
              </p>
              <Button variant="ghost" className="mt-4 text-red-700 hover:bg-red-100" onClick={reset}>
                重新上传
              </Button>
            </div>
          )}
        </div>

        {status === 'parsing' && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded flex items-center gap-2 text-amber-700 text-sm">
            <div className="h-2 w-2 bg-amber-500 rounded-full animate-pulse" />
            文件正在解析中...
          </div>
        )}

        {status === 'success' && parseResult && (
          <div className="mt-4 space-y-3">
            <div className="p-3 bg-green-50 border border-green-100 rounded flex items-center gap-2 text-green-700 text-sm">
              <div className="h-2 w-2 bg-green-500 rounded-full shrink-0" />
              <span>{successMessage}</span>
            </div>
            {canSubmitImport ? (
              <div className="flex justify-center">
                <Button size="lg" onClick={handleSubmit}>
                  提交导入
                </Button>
              </div>
            ) : (
              <p className="text-sm text-center text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-4 py-3 leading-relaxed">
                当前解析结果中没有可导入的有效行，请检查文件后重新上传。
              </p>
            )}
          </div>
        )}
      </Card>

      {!canSubmitImport && status !== 'success' && (
        <p className="mb-4 text-sm text-slate-500 text-center max-w-lg mx-auto leading-relaxed">
          {status === 'idle' && '请先上传文件；解析成功后，点击「提交导入」写入标准库。'}
          {status === 'parsing' && '正在解析，请稍候…'}
          {status === 'error' && '请先上传文件；解析成功后，点击「提交导入」写入标准库。'}
        </p>
      )}

      <div className="mb-4">
        <div className="flex items-center gap-2 text-slate-800 font-bold">
          <FileSpreadsheet className="text-blue-600" size={20} />
          数据预览
        </div>
        {hasValidData ? (
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">
            以下为解析结果预览，<span className="font-medium text-slate-800">尚未写入数据库</span>
            。请点击上方「提交导入」后，标准数据库与工作台「标准动态」才会显示这些数据。
          </p>
        ) : null}
      </div>

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  标准编号
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  标准名称
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  版本号
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  状态
                </th>
                {hasValidData && (
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    验证结果
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {hasValidData ? (
                displayData.map((item: UploadDataItem) => {
                  const badgeInfo = getStatusBadge(item.validation_status);
                  return (
                    <tr key={item.standard_no} className="hover:bg-slate-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                        {item.standard_no}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{item.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{item.version}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge status={item.status === '有效' ? 'active' : 'draft'} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge status={badgeInfo.status} />
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={4}
                    className="px-6 py-14 text-center text-sm text-slate-500"
                  >
                    暂无预览数据。请上传文件，解析成功后将在此显示待导入记录。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default Import;
