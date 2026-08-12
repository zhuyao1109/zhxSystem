import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, ArrowLeft, CheckCircle, XCircle, AlertCircle, FileText, User, Calendar } from 'lucide-react';
import { Card } from '@/components/ui';
import api from '@/api/axios';
import { getApiErrorMessage } from '@/utils/apiError';

interface ImportHistoryItem {
  id: number;
  import_type: string;
  filename: string | null;
  saved_filename: string | null;
  status: string;
  success_count: number;
  failed_count: number;
  error_message: string | null;
  user_id: number;
  username: string | null;
  created_at: string;
}

const ImportHistory: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [histories, setHistories] = useState<ImportHistoryItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [size] = useState(10);

  const loadHistories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/import/history', {
        params: { page, size },
      });

      if (response.code === 200 && response.data) {
        setHistories(response.data.data || []);
        setTotal(response.data.total || 0);
      } else {
        setError(response.message || '加载失败');
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '加载导入历史失败'));
    } finally {
      setLoading(false);
    }
  }, [page, size]);

  useEffect(() => {
    loadHistories().catch(() => {
      // Error handled inside loadHistories
    });
  }, [loadHistories]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">
            <CheckCircle className="w-3 h-3" />
            成功
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-red-100 text-red-700">
            <XCircle className="w-3 h-3" />
            失败
          </span>
        );
      case 'partial':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-700">
            <AlertCircle className="w-3 h-3" />
            部分成功
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 rounded-full text-xs bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getImportTypeLabel = (type: string) => {
    switch (type) {
      case 'upload':
        return '文件上传';
      case 'batch':
        return '批量导入';
      default:
        return type;
    }
  };

  const totalPages = Math.ceil(total / size);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <History className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900">导入历史</h1>
          </div>
        </div>
        <button
          onClick={() => {
            loadHistories().catch(() => {
              // Error handled inside loadHistories
            });
          }}
          className="px-4 py-2 text-sm rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          刷新
        </button>
      </div>

      {error && (
        <Card className="p-4 bg-red-50 border-red-200 text-red-700">
          {error}
        </Card>
      )}

      {loading && (
        <Card className="p-6 text-center text-slate-500">
          加载中...
        </Card>
      )}

      {!loading && histories.length === 0 && (
        <Card className="p-6 text-center text-slate-500">
          暂无导入历史记录
        </Card>
      )}

      {!loading && histories.length > 0 && (
        <div className="space-y-3">
          {histories.map((item) => (
            <Card key={item.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-2">
                  {/* 第一行：类型、状态、文件名 */}
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">
                      {getImportTypeLabel(item.import_type)}
                    </span>
                    {getStatusBadge(item.status)}
                    {item.filename && (
                      <div className="flex items-center gap-1 text-sm text-slate-600">
                        <FileText className="w-4 h-4" />
                        {item.filename}
                      </div>
                    )}
                  </div>

                  {/* 第二行：统计信息 */}
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-green-600">
                      成功: {item.success_count}
                    </span>
                    {item.failed_count > 0 && (
                      <span className="text-red-600">
                        失败: {item.failed_count}
                      </span>
                    )}
                  </div>

                  {/* 第三行：错误信息 */}
                  {item.error_message && (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      {item.error_message}
                    </div>
                  )}

                  {/* 第四行：操作信息 */}
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {item.username || `用户${item.user_id}`}
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(item.created_at).toLocaleString('zh-CN')}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 分页 */}
      {!loading && totalPages > 1 && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600">
              共 {total} 条记录，第 {page} / {totalPages} 页
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default ImportHistory;
