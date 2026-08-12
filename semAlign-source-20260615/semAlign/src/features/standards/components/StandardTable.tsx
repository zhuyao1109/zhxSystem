import React from 'react';
import { Download, Edit2, Eye, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui';
import type { Standard } from '@/types';

const TABLE_SKELETON_KEYS = [
  'table-skeleton-1',
  'table-skeleton-2',
  'table-skeleton-3',
  'table-skeleton-4',
  'table-skeleton-5',
] as const;

export interface StandardTableProps {
  standards: Standard[];
  loading?: boolean;
  onEdit?: (standard: Standard) => void;
  onDelete?: (standard: Standard) => void;
  onView?: (standard: Standard) => void;
  onDownload?: (standard: Standard) => void;
}

export const StandardTable: React.FC<StandardTableProps> = ({
  standards,
  loading,
  onEdit,
  onDelete,
  onView,
  onDownload,
}) => {
  if (loading) {
    return (
      <div className="animate-pulse space-y-3 p-4">
        {TABLE_SKELETON_KEYS.map((key) => (
          <div key={key} className="h-12 bg-slate-200 rounded" />
        ))}
      </div>
    );
  }

  if (standards.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p>暂无数据</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">标准编号</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">标准名称</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">状态</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">主管部门</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">发布日期</th>
            <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {standards.map((standard) => (
            <tr key={standard.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 text-sm">
                <span className="font-mono text-blue-600">{standard.code}</span>
              </td>
              <td className="px-4 py-3 text-sm">
                <div>
                  <div className="font-medium text-slate-900">{standard.name}</div>
                  <div className="text-xs text-slate-400">{standard.description}</div>
                </div>
              </td>
              <td className="px-4 py-3 text-sm">
                <Badge status={standard.status} />
              </td>
              <td className="px-4 py-3 text-sm text-slate-700">{standard.department}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{standard.date}</td>
              <td className="px-4 py-3 text-sm">
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={() => onView?.(standard)}
                    className="p-1 rounded hover:bg-slate-100 text-slate-600 transition-colors"
                    title="查看详情"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDownload?.(standard)}
                    className="p-1 rounded hover:bg-slate-100 text-slate-600 transition-colors"
                    title="下载文档"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onEdit?.(standard)}
                    className="p-1 rounded hover:bg-blue-50 text-blue-600 transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDelete?.(standard)}
                    className="p-1 rounded hover:bg-red-50 text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default StandardTable;
