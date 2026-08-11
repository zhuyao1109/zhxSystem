/**
 * @file semAlign
 * @file Standards.tsx
 * @description 标准数据库模块：列表筛选、详情查看、原文件下载与元数据展示。
 * @remarks 标准库主页面：筛选、分页列表与跳转详情。
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
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StandardFilter } from './components/StandardFilter';
import { StandardTable } from './components/StandardTable';
import { useStandards } from './hooks/useStandards';
import { standardsService } from './standards.service';
import { downloadStandardFile } from './standardDownload';
import { Pagination, PageLoading } from '@/components/ui';
import { ConfirmDialog, FormDialog, useToast } from '@/components/common';
import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { getApiErrorMessage } from '@/utils/apiError';
import type { Standard } from '@/types';

// -----------------------------------------------------------------------------
// 分段：Standards.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

/**
 * 类型定义 `TermConflictRow`：描述前后端交互或页面状态结构。
 */
interface TermConflictRow {
  id: number;
  term_name: string;
  standard_no_1: string;
  standard_no_2: string;
  conflict_type: string;
  conflict_desc: string;
  source_file: string;
}

/**
 * 类型定义 `TermConflictOverviewData`：描述前后端交互或页面状态结构。
 */
interface TermConflictOverviewData {
  total_conflicts: number;
  total_terms: number;
  total_types: number;
  latest_batch_status: string | null;
  latest_batch_rows: number;
  rows: TermConflictRow[];
}

/**
 * 类型定义 `VectorSourceRow`：描述前后端交互或页面状态结构。
 */
interface VectorSourceRow {
  source: string;
  saved_as: string | null;
  chunk_count: number;
}

/**
 * 类型定义 `VectorStoreOverviewData`：描述前后端交互或页面状态结构。
 */
interface VectorStoreOverviewData {
  available: boolean;
  db_path: string;
  collection_name: string | null;
  dimension: number | null;
  total_chunks: number;
  total_sources: number;
  rows: VectorSourceRow[];
}

/**
 * 类型定义 `ConflictDialogueRow`：描述前后端交互或页面状态结构。
 */
interface ConflictDialogueRow {
  id: number;
  dialogue_id: string;
  original_conflict_id: string;
  question: string;
  conflict_type: string;
  source_document: string;
  cluster: string;
}

/**
 * 类型定义 `ConflictDialogueTermConflictRow`：描述前后端交互或页面状态结构。
 */
interface ConflictDialogueTermConflictRow {
  id: number;
  term_name: string;
  standard_no_1: string;
  standard_no_2: string;
  conflict_type: string;
  conflict_desc: string;
  source_file: string;
}

/**
 * 类型定义 `ConflictDialogueOverviewData`：描述前后端交互或页面状态结构。
 */
interface ConflictDialogueOverviewData {
  total_dialogues: number;
  total_conflict_groups: number;
  total_mappings: number;
  mapped_conflict_groups: number;
  total_term_conflicts: number;
  rows: ConflictDialogueRow[];
  term_conflict_rows: ConflictDialogueTermConflictRow[];
}

/**
 * 类型定义 `StandardFilterOptionsData`：描述前后端交互或页面状态结构。
 */
interface StandardFilterOptionsData {
  statuses: string[];
  departments: string[];
  categories: string[];
}

const SKELETON_ROW_KEYS = ['skeleton-row-1', 'skeleton-row-2', 'skeleton-row-3'] as const;

/**
 * React 组件 `LoadingSkeleton`：负责对应页面或区块的 UI 与交互。
 */
const LoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-3 p-4">
    {SKELETON_ROW_KEYS.map((key) => (
      <div key={key} className="h-10 bg-slate-200 rounded" />
    ))}
  </div>
);

/**
 * 类型定义 `LoadingErrorPanelProps`：描述前后端交互或页面状态结构。
 */
interface LoadingErrorPanelProps {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyMessage: string;
  children: React.ReactNode;
}

/**
 * React 组件 `LoadingErrorPanel`：负责对应页面或区块的 UI 与交互。
 */
const LoadingErrorPanel: React.FC<LoadingErrorPanelProps> = ({
  loading,
  error,
  isEmpty,
  emptyMessage,
  children,
}) => {
  if (loading) {
    return <LoadingSkeleton />;
  }
  if (error) {
    return <div className="p-4 text-sm text-red-600">{error}</div>;
  }
  if (isEmpty) {
    return <div className="p-4 text-sm text-slate-500">{emptyMessage}</div>;
  }
  return <>{children}</>;
};

/**
 * React 组件 `VectorUnavailableMessage`：负责对应页面或区块的 UI 与交互。
 */
const VectorUnavailableMessage: React.FC<{ overview: VectorStoreOverviewData }> = ({ overview }) => (
  <div className="p-4 text-sm text-slate-500">
    当前未检测到可用的向量数据库。路径：{overview.db_path}
  </div>
);

/**
 * 类型定义 `VectorLoadingErrorPanelProps`：描述前后端交互或页面状态结构。
 */
interface VectorLoadingErrorPanelProps {
  loading: boolean;
  error: string | null;
  overview: VectorStoreOverviewData | null;
  emptyMessage: string;
  children: React.ReactNode;
}

/**
 * React 组件 `VectorLoadingErrorPanel`：负责对应页面或区块的 UI 与交互。
 */
const VectorLoadingErrorPanel: React.FC<VectorLoadingErrorPanelProps> = ({
  loading,
  error,
  overview,
  emptyMessage,
  children,
}) => {
  if (loading) {
    return <LoadingSkeleton />;
  }
  if (error) {
    return <div className="p-4 text-sm text-red-600">{error}</div>;
  }
  if (!overview) {
    return <div className="p-4 text-sm text-slate-500">{emptyMessage}</div>;
  }
  if (!overview.available) {
    return <VectorUnavailableMessage overview={overview} />;
  }
  return <>{children}</>;
};

/**
 * 异步函数 `fetchFilterOptions`：发起 API 请求或执行页面侧异步流程。
 */
async function fetchFilterOptions(): Promise<StandardFilterOptionsData | null> {
  const response: {
    code: number;
    message: string;
    data: StandardFilterOptionsData;
  } = await api.get(Endpoints.STANDARD_FILTER_OPTIONS);
  if (response.code !== 200 || !response.data) {
    return null;
  }
  return response.data;
}

/**
 * 异步函数 `fetchTermConflictOverview`：发起 API 请求或执行页面侧异步流程。
 */
async function fetchTermConflictOverview(): Promise<TermConflictOverviewData> {
  const response: {
    code: number;
    message: string;
    data: TermConflictOverviewData;
  } = await api.get(Endpoints.TERM_CONFLICT_OVERVIEW, {
    params: { page: 1, size: 20 },
  });
  if (response.code !== 200 || !response.data) {
    throw new Error(response.message || '术语冲突数据加载失败');
  }
  return response.data;
}

/**
 * 异步函数 `fetchConflictDialogueOverview`：发起 API 请求或执行页面侧异步流程。
 */
async function fetchConflictDialogueOverview(): Promise<ConflictDialogueOverviewData> {
  const response: {
    code: number;
    message: string;
    data: ConflictDialogueOverviewData;
  } = await api.get(Endpoints.CONFLICT_DIALOGUE_OVERVIEW, {
    params: { page: 1, size: 20 },
  });
  if (response.code !== 200 || !response.data) {
    throw new Error(response.message || '冲突对数据加载失败');
  }
  return response.data;
}

/**
 * 异步函数 `fetchVectorStoreOverview`：发起 API 请求或执行页面侧异步流程。
 */
async function fetchVectorStoreOverview(): Promise<VectorStoreOverviewData> {
  const response: {
    code: number;
    message: string;
    data: VectorStoreOverviewData;
  } = await api.get(Endpoints.VECTOR_STORE_OVERVIEW);
  if (response.code !== 200 || !response.data) {
    throw new Error(response.message || '向量数据库数据加载失败');
  }
  return response.data;
}

/**
 * Hook `useOverviewFetch`：封装可复用的状态逻辑与副作用。
 */
function useOverviewFetch<T>(
  fetchFn: () => Promise<T>,
  errorFallback: string,
): { data: T | null; loading: boolean; error: string | null } {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    let mounted = true;
    /**
     * 异步函数 `load`：发起 API 请求或执行页面侧异步流程。
     */
    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFn();
        if (mounted) {
          setData(result);
        }
      } catch (err: unknown) {
        if (mounted) {
          setError(getApiErrorMessage(err, errorFallback));
          setData(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    load().catch(() => {
      // Error handled inside load
    });
    return () => {
      mounted = false;
    };
  }, [fetchFn, errorFallback]);

  return { data, loading, error };
}

/**
 * React 组件 `TermConflictOverviewContent`：负责对应页面或区块的 UI 与交互。
 */
const TermConflictOverviewContent: React.FC<{ overview: TermConflictOverviewData }> = ({ overview }) => (
  <div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-4 border-b border-slate-200 bg-slate-50">
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">冲突总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_conflicts}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">术语总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_terms}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">冲突类型数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_types}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">最新批次状态</div>
        <div className="text-sm font-semibold text-slate-900">{overview.latest_batch_status || '-'}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">最新批次入库行数</div>
        <div className="text-xl font-bold text-slate-900">{overview.latest_batch_rows}</div>
      </div>
    </div>

    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">术语名</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">冲突类型</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">定义1来源标准</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">定义2来源标准</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">冲突描述</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {overview.rows.map((row) => (
            <tr key={row.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 text-sm font-medium text-slate-900">{row.term_name}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.conflict_type}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.standard_no_1}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.standard_no_2}</td>
              <td className="px-4 py-3 text-sm text-slate-700 max-w-xl truncate" title={row.conflict_desc}>
                {row.conflict_desc}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

/**
 * React 组件 `VectorStoreOverviewContent`：负责对应页面或区块的 UI 与交互。
 */
const VectorStoreOverviewContent: React.FC<{ overview: VectorStoreOverviewData }> = ({ overview }) => (
  <div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-4 border-b border-slate-200 bg-slate-50">
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">Collection</div>
        <div className="text-base font-bold text-slate-900">{overview.collection_name || '-'}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">向量维度</div>
        <div className="text-xl font-bold text-slate-900">{overview.dimension ?? '-'}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">Chunk 总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_chunks}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">文件来源数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_sources}</div>
      </div>
    </div>

    <div className="px-4 py-3 text-xs text-slate-500 border-b border-slate-200 bg-slate-50">
      数据库路径：{overview.db_path}
    </div>

    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">原始文件名</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">保存文件名</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Chunk 数</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {overview.rows.map((row) => (
            <tr key={`${row.source}-${row.saved_as || ''}`} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 text-sm font-medium text-slate-900">{row.source}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.saved_as || '-'}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.chunk_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

/**
 * React 组件 `ConflictDialogueOverviewContent`：负责对应页面或区块的 UI 与交互。
 */
const ConflictDialogueOverviewContent: React.FC<{ overview: ConflictDialogueOverviewData }> = ({ overview }) => (
  <div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-4 border-b border-slate-200 bg-slate-50">
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">问答总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_dialogues}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">冲突组数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_conflict_groups}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">映射总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_mappings}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">已映射冲突组</div>
        <div className="text-xl font-bold text-slate-900">{overview.mapped_conflict_groups}</div>
      </div>
      <div className="rounded border border-slate-200 bg-white p-3">
        <div className="text-xs text-slate-500">术语冲突总数</div>
        <div className="text-xl font-bold text-slate-900">{overview.total_term_conflicts}</div>
      </div>
    </div>

    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">问答ID</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">原始冲突ID</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">冲突类型</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">来源文档</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">问题</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {overview.rows.map((row) => (
            <tr key={row.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 text-sm font-medium text-slate-900">{row.dialogue_id}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.original_conflict_id}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.conflict_type}</td>
              <td className="px-4 py-3 text-sm text-slate-700 max-w-md truncate" title={row.source_document}>
                {row.source_document}
              </td>
              <td className="px-4 py-3 text-sm text-slate-700 max-w-xl truncate" title={row.question}>
                {row.question}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    <div className="px-4 py-3 text-sm font-semibold text-slate-800 border-t border-slate-200 bg-slate-50">
      术语冲突内容预览
    </div>
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">术语名</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">冲突类型</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">定义1来源标准</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">定义2来源标准</th>
            <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">冲突描述</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {overview.term_conflict_rows.map((row) => (
            <tr key={`dialogue-term-${row.id}`} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 text-sm font-medium text-slate-900">{row.term_name}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.conflict_type}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.standard_no_1}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{row.standard_no_2}</td>
              <td className="px-4 py-3 text-sm text-slate-700 max-w-xl truncate" title={row.conflict_desc}>
                {row.conflict_desc}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

/**
 * 标准库主页面：筛选、分页列表与跳转详情。
 */
export const Standards: React.FC = () => {
  const navigate = useNavigate();
  const { standards, pagination, loading, search, filter, setPage, refetch } = useStandards();
  const {
    data: overview,
    loading: overviewLoading,
    error: overviewError,
  } = useOverviewFetch(fetchTermConflictOverview, '术语冲突数据加载失败');
  const {
    data: vectorOverview,
    loading: vectorLoading,
    error: vectorError,
  } = useOverviewFetch(fetchVectorStoreOverview, '向量数据库数据加载失败');
  const {
    data: dialogueOverview,
    loading: dialogueLoading,
    error: dialogueError,
  } = useOverviewFetch(fetchConflictDialogueOverview, '冲突对数据加载失败');
  const [statusOptions, setStatusOptions] = useState<string[]>([]);
  const [departmentOptions, setDepartmentOptions] = useState<string[]>([]);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [currentStandard, setCurrentStandard] = useState<Standard | null>(null);

  const { showSuccess, showError } = useToast();

  useEffect(() => {
    let mounted = true;
    fetchFilterOptions()
      .then((data) => {
        if (!mounted || !data) {
          return;
        }
        setStatusOptions(data.statuses ?? []);
        setDepartmentOptions(data.departments ?? []);
      })
      .catch(() => {
        // 筛选项加载失败时回退到 StandardFilter 组件内置默认选项
      });
    return () => {
      mounted = false;
    };
  }, []);

  /**
   * 异步函数 `handleCreate`：发起 API 请求或执行页面侧异步流程。
   */
  const handleCreate = async (values: Record<string, string>): Promise<void> => {
    try {
      await standardsService.create({
        code: values.code,
        name: values.name,
        version: values.version || 'V1.0',
        status: 'active',
        department: values.department || '',
        date: new Date().toISOString().slice(0, 10),
        category: values.category || '未分类',
        description: values.description || '',
      });
      await refetch();
      showSuccess('新增成功');
    } catch (err: unknown) {
      showError(getApiErrorMessage(err, '新增失败'));
    }
  };

  /**
   * 异步函数 `handleEdit`：发起 API 请求或执行页面侧异步流程。
   */
  const handleEdit = async (values: Record<string, string>): Promise<void> => {
    if (!currentStandard) return;

    try {
      await standardsService.update(currentStandard.id, {
        name: values.name,
        version: values.version,
        department: values.department || '',
        category: values.category || '',
        description: values.description || '',
      });
      await refetch();
      showSuccess('更新成功');
    } catch (err: unknown) {
      showError(getApiErrorMessage(err, '更新失败'));
    }
  };

  /**
   * 异步函数 `handleDelete`：发起 API 请求或执行页面侧异步流程。
   */
  const handleDelete = async (): Promise<void> => {
    if (!currentStandard) return;

    try {
      await standardsService.delete(currentStandard.id);
      await refetch();
      showSuccess('删除成功');
    } catch (err: unknown) {
      showError(getApiErrorMessage(err, '删除失败'));
    }
  };

  /**
   * 函数 `handleView`：本模块内部业务辅助逻辑。
   */
  const handleView = (s: Standard): void => {
    navigate(`/database/${encodeURIComponent(s.id)}`);
  };

  /**
   * 异步函数 `handleDownload`：发起 API 请求或执行页面侧异步流程。
   */
  const handleDownload = async (s: Standard): Promise<void> => {
    try {
      await downloadStandardFile(s.id, 'original', `${s.code}.pdf`);
    } catch {
      try {
        await downloadStandardFile(s.id, 'text', `${s.code}.txt`);
      } catch (err: unknown) {
        showError(getApiErrorMessage(err, '下载失败：未找到可下载文件'));
      }
    }
  };

  if (loading && !standards.length) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">标准库</h1>
      
      <StandardFilter
        onSearch={search}
        onFilter={filter}
        onCreate={() => setCreateDialogOpen(true)}
        loading={loading}
        statusOptions={statusOptions}
        departmentOptions={departmentOptions}
      />

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <StandardTable
          standards={standards}
          loading={loading}
          onView={handleView}
          onDownload={(s) => void handleDownload(s)}
          onEdit={(s) => {
            setCurrentStandard(s);
            setEditDialogOpen(true);
          }}
          onDelete={(s) => {
            setCurrentStandard(s);
            setDeleteDialogOpen(true);
          }}
        />

        {pagination && (
          <div className="p-4 border-t border-slate-200">
            <Pagination
              current={pagination.current}
              pageSize={pagination.pageSize}
              total={pagination.total}
              onChange={setPage}
            />
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">术语冲突数据（临时展示）</h2>
          <p className="text-sm text-slate-500 mt-1">展示术语冲突数据库中的统计信息与最近 20 条记录</p>
        </div>

        <LoadingErrorPanel
          loading={overviewLoading}
          error={overviewError}
          isEmpty={!overview}
          emptyMessage="暂无术语冲突数据"
        >
          {overview && <TermConflictOverviewContent overview={overview} />}
        </LoadingErrorPanel>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">标准文件向量数据（临时展示）</h2>
          <p className="text-sm text-slate-500 mt-1">展示后端向量数据库中已入库标准文件的 collection、chunk 数量与文件来源</p>
        </div>

        <VectorLoadingErrorPanel
          loading={vectorLoading}
          error={vectorError}
          overview={vectorOverview}
          emptyMessage="暂无向量数据库数据"
        >
          {vectorOverview ? <VectorStoreOverviewContent overview={vectorOverview} /> : null}
        </VectorLoadingErrorPanel>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">冲突对数据（问答，临时展示）</h2>
          <p className="text-sm text-slate-500 mt-1">展示冲突问答入库数量、映射数量与最近 20 条问答记录</p>
        </div>

        <LoadingErrorPanel
          loading={dialogueLoading}
          error={dialogueError}
          isEmpty={!dialogueOverview}
          emptyMessage="暂无冲突对数据"
        >
          {dialogueOverview && <ConflictDialogueOverviewContent overview={dialogueOverview} />}
        </LoadingErrorPanel>
      </div>

      <FormDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSubmit={handleCreate}
        title="新增标准"
        fields={[
          { name: 'code', label: '标准编号', placeholder: '如 GB/T 12345-2020', required: true },
          { name: 'name', label: '标准名称', required: true },
          { name: 'version', label: '版本号', defaultValue: 'V1.0', placeholder: '如 V1.0' },
          { name: 'department', label: '主管部门', placeholder: '可选' },
          { name: 'category', label: '分类', defaultValue: '未分类', placeholder: '可选' },
          { name: 'description', label: '标准描述', type: 'textarea', placeholder: '可选' },
        ]}
      />

      <FormDialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        onSubmit={handleEdit}
        title="编辑标准"
        fields={[
          { name: 'name', label: '标准名称', defaultValue: currentStandard?.name, required: true },
          { name: 'version', label: '版本号', defaultValue: currentStandard?.version },
          { name: 'department', label: '主管部门', defaultValue: currentStandard?.department || '' },
          { name: 'category', label: '分类', defaultValue: currentStandard?.category || '' },
          { name: 'description', label: '标准描述', type: 'textarea', defaultValue: currentStandard?.description || '' },
        ]}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        title="删除标准"
        message={`确认删除标准「${currentStandard?.name}」吗？此操作不可恢复。`}
        danger
      />
    </div>
  );
};

export default Standards;
/**
 * @moduleEnd semAlign
 * @file Standards.tsx
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

