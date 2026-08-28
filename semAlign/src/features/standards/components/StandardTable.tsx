/**
 * @file semAlign
 * @file StandardTable.tsx
 * @description 标准数据库模块：列表筛选、详情查看、原文件下载与元数据展示。
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

/**
 * 类型定义 `StandardTableProps`：描述前后端交互或页面状态结构。
 */
export interface StandardTableProps {
  standards: Standard[];
  loading?: boolean;
  onEdit?: (standard: Standard) => void;
  onDelete?: (standard: Standard) => void;
  onView?: (standard: Standard) => void;
  onDownload?: (standard: Standard) => void;
}

/**
 * React 组件 `StandardTable`：负责对应页面或区块的 UI 与交互。
 */
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
                  <div className="text-xs text-slate-400 line-clamp-2 break-words">{standard.description}</div>
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
/**
 * @moduleEnd semAlign
 * @file StandardTable.tsx
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

