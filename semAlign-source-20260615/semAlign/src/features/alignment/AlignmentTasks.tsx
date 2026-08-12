import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trash2, RefreshCw } from 'lucide-react';

import { Card, Pagination } from '@/components/ui';
import { ConfirmDialog, useToast } from '@/components/common';
import { alignmentService } from './alignment.service';
import { getApiErrorMessage } from '@/utils/apiError';

interface TaskRow {
  taskId: string;
  status: string;
  reviewStatus?: string;
  created_at?: string;
  inputTextPreview?: string;
}

function statusStyle(status: string): string {
  if (status === 'completed') {
    return 'bg-emerald-100 text-emerald-700';
  }
  if (status === 'processing') {
    return 'bg-amber-100 text-amber-700';
  }
  if (status === 'failed') {
    return 'bg-rose-100 text-rose-700';
  }
  return 'bg-slate-100 text-slate-700';
}

const AlignmentTasks: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);
  const [deleteTaskId, setDeleteTaskId] = useState<string | null>(null);
  const [reviewingTaskId, setReviewingTaskId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const { showSuccess, showError } = useToast();

  const loadTasks = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await alignmentService.getTaskList({ page, size: pageSize });
      setTasks(response.data?.data || []);
      setTotal(response.data?.total || 0);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '加载任务列表失败'));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadTasks().catch(() => {});
  }, [loadTasks]);

  const handleRefresh = useCallback((): void => {
    loadTasks().catch(() => {});
  }, [loadTasks]);

  const handleRetry = async (taskId: string): Promise<void> => {
    setRetryingTaskId(taskId);
    setError(null);
    try {
      await alignmentService.retryTask(taskId);
      await loadTasks();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '重新对齐失败'));
    } finally {
      setRetryingTaskId(null);
    }
  };

  const handleReview = async (
    taskId: string,
    action: 'submit' | 'approve' | 'reject' | 'publish',
    notes?: string
  ): Promise<void> => {
    setReviewingTaskId(taskId);
    try {
      await alignmentService.reviewTask(taskId, action, notes);
      showSuccess('审核状态已更新');
      await loadTasks();
    } catch (err: unknown) {
      showError(getApiErrorMessage(err, '更新审核状态失败'));
    } finally {
      setReviewingTaskId(null);
    }
  };

  const handleDelete = async (taskId: string): Promise<void> => {
    try {
      await alignmentService.deleteTask(taskId);
      showSuccess(`任务 #${taskId} 已删除`);
      await loadTasks();
    } catch (err: unknown) {
      const message = getApiErrorMessage(err, '删除任务失败');
      setError(message);
      showError(message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">对齐任务管理</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="px-3 py-2 text-sm rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            刷新
          </button>
          <button
            onClick={() => navigate('/alignment')}
            className="px-3 py-2 text-sm rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50"
          >
            新建任务
          </button>
        </div>
      </div>

      {loading && <Card className="text-slate-500">正在加载任务列表...</Card>}
      {!loading && error && <Card className="text-red-600">{error}</Card>}

      {!loading && !error && (
        <Card>
          {tasks.length === 0 ? (
            <div className="text-sm text-slate-500">暂无历史任务。</div>
          ) : (
            <div className="space-y-4">
              <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">任务ID</th>
                    <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">状态</th>
                    <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">审核状态</th>
                    <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">创建时间</th>
                    <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">输入摘要</th>
                    <th className="px-3 py-2 text-center text-sm font-medium text-slate-600">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {tasks.map((task) => (
                    <tr key={task.taskId} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-sm font-mono text-slate-900">#{task.taskId}</td>
                      <td className="px-3 py-2 text-sm">
                        <span className={`inline-flex px-2 py-1 rounded ${statusStyle(task.status)}`}>
                          {task.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-sm text-slate-700">{task.reviewStatus || 'draft'}</td>
                      <td className="px-3 py-2 text-sm text-slate-700">{task.created_at || '-'}</td>
                      <td className="px-3 py-2 text-sm text-slate-700 max-w-[360px] truncate">
                        {task.inputTextPreview || '-'}
                      </td>
                      <td className="px-3 py-2 text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <Link
                            className="px-2 py-1 rounded border border-slate-300 text-slate-700 hover:bg-slate-100"
                            to={`/alignment/result?taskId=${encodeURIComponent(task.taskId)}`}
                          >
                            查看
                          </Link>
                          {task.status === 'completed' && task.reviewStatus !== 'published' && (
                            <button
                              onClick={() => void handleReview(task.taskId, task.reviewStatus === 'draft' ? 'submit' : 'approve')}
                              disabled={reviewingTaskId === task.taskId}
                              className="px-2 py-1 rounded border border-emerald-300 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                              title={task.reviewStatus === 'draft' ? '提交审核' : '审核通过'}
                            >
                              {task.reviewStatus === 'draft' ? '提交' : '通过'}
                            </button>
                          )}
                          {task.reviewStatus === 'approved' && (
                            <button
                              onClick={() => void handleReview(task.taskId, 'publish')}
                              disabled={reviewingTaskId === task.taskId}
                              className="px-2 py-1 rounded border border-blue-300 text-blue-700 hover:bg-blue-50 disabled:opacity-50"
                              title="发布给普通用户查看"
                            >
                              发布
                            </button>
                          )}
                          <button
                            onClick={() => void handleRetry(task.taskId)}
                            disabled={retryingTaskId === task.taskId}
                            className="p-1 rounded text-blue-600 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="重新对齐"
                          >
                            <RefreshCw size={16} className={retryingTaskId === task.taskId ? 'animate-spin' : ''} />
                          </button>
                          <button
                            onClick={() => setDeleteTaskId(task.taskId)}
                            className="p-1 rounded text-rose-600 hover:bg-rose-50"
                            title="删除任务"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                onChange={setPage}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setPage(1);
                }}
              />
            </div>
          )}
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(deleteTaskId)}
        onClose={() => setDeleteTaskId(null)}
        onConfirm={() => {
          if (deleteTaskId) {
            void handleDelete(deleteTaskId);
          }
        }}
        title="删除对齐任务"
        message={`确认删除任务 #${deleteTaskId ?? ''} 吗？删除后不可恢复。`}
        confirmText="删除"
        danger
      />
    </div>
  );
};

export default AlignmentTasks;
