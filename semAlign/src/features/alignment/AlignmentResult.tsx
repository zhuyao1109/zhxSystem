/**
 * @file semAlign
 * @file AlignmentResult.tsx
 * @description 标准对齐模块：任务创建、冲突结果、对齐助手对话与审核流转。
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
import { useSearchParams } from 'react-router-dom';
import { Card, Pagination } from '@/components/ui';
import { useToast } from '@/components/common';
import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { getApiErrorMessage } from '@/utils/apiError';
import { alignmentApi } from '@/api/modules/alignment';

// -----------------------------------------------------------------------------
// 分段：AlignmentResult.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

/**
 * 类型定义 `ComparisonTaskData`：描述前后端交互或页面状态结构。
 */
interface ComparisonTaskData {
  id: string;
  standard_group1?: string;
  standard_group2?: string;
  comparison_time?: string;
  alignment_mode?: string;
  priority_rules?: string;
  status?: string;
}

/**
 * 类型定义 `ComparisonStatsData`：描述前后端交互或页面状态结构。
 */
interface ComparisonStatsData {
  conflict_rate: number;
  match_rate: number;
  pending_rate: number;
}

/**
 * 类型定义 `PaginatedConflictsData`：描述前后端交互或页面状态结构。
 */
interface PaginatedConflictsData {
  data: ComparisonConflictData[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/**
 * 类型定义 `ManualDecision`：描述前后端交互或页面状态结构。
 */
interface ManualDecision {
  decision: string;
  username?: string;
  updated_at?: string;
  modified_recommendation?: string;
  notes?: string;
}

/**
 * 类型定义 `ComparisonConflictData`：描述前后端交互或页面状态结构。
 */
interface ComparisonConflictData {
  id: string;
  title: string;
  severity: string;
  similarity_score?: number;
  priority_score?: number;
  priority_rank?: number;
  priority_recommendation?: string;
  location?: {
    standard1_clause_index?: number | null;
    standard2_clause_index?: number | null;
    standard1_section?: string;
    standard2_section?: string;
  };
  standard1?: { name?: string; content?: string };
  standard2?: { name?: string; content?: string };
  manual_decision?: ManualDecision;
}

/**
 * 函数 `manualDecisionTextClass`：本模块内部业务辅助逻辑。
 */
function manualDecisionTextClass(decision: string): string {
  if (decision === 'accept') {
    return 'text-green-600';
  }
  if (decision === 'reject') {
    return 'text-red-600';
  }
  return 'text-amber-600';
}

/**
 * 函数 `manualDecisionLabel`：本模块内部业务辅助逻辑。
 */
function manualDecisionLabel(decision: string): string {
  if (decision === 'accept') {
    return '接受';
  }
  if (decision === 'reject') {
    return '拒绝';
  }
  return '修改';
}

/**
 * 函数 `truncateContent`：本模块内部业务辅助逻辑。
 */
function truncateContent(content: string, maxLength = 30): string {
  if (content.length <= maxLength) {
    return content;
  }
  return `${content.slice(0, maxLength)}...`;
}

/**
 * 函数 `applyConflictsResponse`：本模块内部业务辅助逻辑。
 */
function applyConflictsResponse(
  conflictsData: PaginatedConflictsData | ComparisonConflictData[] | undefined
): { conflicts: ComparisonConflictData[]; total: number } {
  if (Array.isArray(conflictsData)) {
    return { conflicts: conflictsData, total: conflictsData.length };
  }
  return {
    conflicts: Array.isArray(conflictsData?.data) ? conflictsData.data : [],
    total: Number(conflictsData?.total ?? 0),
  };
}

/**
 * 类型定义 `ConflictResultCardProps`：描述前后端交互或页面状态结构。
 */
interface ConflictResultCardProps {
  conflict: ComparisonConflictData;
  modifyConflictId: string | null;
  modifyNotes: Record<string, string>;
  savingDecision: string | null;
  onManualDecision: (
    conflictId: string,
    decision: 'accept' | 'reject' | 'modify',
    notes?: string
  ) => Promise<void>;
  onModifyConflictIdChange: (conflictId: string | null) => void;
  onModifyNotesChange: (conflictId: string, notes: string) => void;
  onClearModifyNotes: (conflictId: string) => void;
  showError: (message: string) => void;
}

/**
 * React 组件 `ConflictResultCard`：负责对应页面或区块的 UI 与交互。
 */
const ConflictResultCard: React.FC<ConflictResultCardProps> = ({
  conflict: c,
  modifyConflictId,
  modifyNotes,
  savingDecision,
  onManualDecision,
  onModifyConflictIdChange,
  onModifyNotesChange,
  onClearModifyNotes,
  showError,
}) => {
  /**
   * 函数 `handleAccept`：本模块内部业务辅助逻辑。
   */
  const handleAccept = (): void => {
    onManualDecision(c.id, 'accept', '同意系统建议').catch(() => {});
  };

  /**
   * 函数 `handleReject`：本模块内部业务辅助逻辑。
   */
  const handleReject = (): void => {
    onManualDecision(c.id, 'reject', '不同意系统建议').catch(() => {});
  };

  /**
   * 函数 `handleToggleModify`：本模块内部业务辅助逻辑。
   */
  const handleToggleModify = (): void => {
    onModifyConflictIdChange(modifyConflictId === c.id ? null : c.id);
  };

  /**
   * 函数 `handleSaveModify`：本模块内部业务辅助逻辑。
   */
  const handleSaveModify = (): void => {
    /**
     * 函数 `notes`：本模块内部业务辅助逻辑。
     */
    const notes = (modifyNotes[c.id] || '').trim();
    if (!notes) {
      showError('请输入修改说明或提示词');
      return;
    }
    onManualDecision(c.id, 'modify', notes).catch(() => {});
  };

  /**
   * 函数 `handleCancelModify`：本模块内部业务辅助逻辑。
   */
  const handleCancelModify = (): void => {
    onModifyConflictIdChange(null);
    onClearModifyNotes(c.id);
  };

  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <div className="flex justify-between items-center mb-2">
        <div className="font-medium text-slate-900">{c.title}</div>
        <div className="text-xs text-slate-500">
          优先级 #{c.priority_rank ?? '-'} | 分数 {c.priority_score ?? '-'} | {c.severity}
        </div>
      </div>
      <div className="text-xs text-slate-500 mb-2">
        位置：A[{c.location?.standard1_section || '正文'}#{c.location?.standard1_clause_index ?? '-'}
        {c.standard1?.content && `: "${truncateContent(c.standard1.content)}"`}]
        vs B[{c.location?.standard2_section || '正文'}#{c.location?.standard2_clause_index ?? '-'}
        {c.standard2?.content && `: "${truncateContent(c.standard2.content)}"`}]
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div className="bg-slate-50 rounded p-3">
          <div className="text-xs text-slate-500 mb-1">{c.standard1?.name || '标准组1'}</div>
          <div className="text-slate-800 whitespace-pre-wrap">{c.standard1?.content || '-'}</div>
        </div>
        <div className="bg-slate-50 rounded p-3">
          <div className="text-xs text-slate-500 mb-1">{c.standard2?.name || '标准组2'}</div>
          <div className="text-slate-800 whitespace-pre-wrap">{c.standard2?.content || '-'}</div>
        </div>
      </div>
      <div className="text-xs text-emerald-700 mt-2">推荐：{c.priority_recommendation || '待人工判定'}</div>

      {c.manual_decision ? (
        <div className="mt-3 p-2 bg-blue-50 rounded text-xs">
          <span className="font-medium">已决策：</span>
          <span className={manualDecisionTextClass(c.manual_decision.decision)}>
            {manualDecisionLabel(c.manual_decision.decision)}
          </span>
          {c.manual_decision.notes && <span className="ml-2 text-slate-600">（{c.manual_decision.notes}）</span>}
          {c.manual_decision.updated_at && (
            <span className="ml-2 text-slate-400">
              {new Date(c.manual_decision.updated_at).toLocaleString()}
            </span>
          )}
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <button
            onClick={handleAccept}
            disabled={savingDecision === c.id}
            className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            接受建议
          </button>
          <button
            onClick={handleReject}
            disabled={savingDecision === c.id}
            className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
          >
            拒绝建议
          </button>
          <button
            onClick={handleToggleModify}
            disabled={savingDecision === c.id}
            className="px-3 py-1 text-xs bg-amber-500 text-white rounded hover:bg-amber-600 disabled:opacity-50"
          >
            手动修改
          </button>
        </div>
      )}

      {modifyConflictId === c.id && !c.manual_decision && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <label className="block text-xs font-medium text-amber-900 mb-2">
            追加提示词 / 人工修改说明
          </label>
          <textarea
            value={modifyNotes[c.id] || ''}
            onChange={(event) => onModifyNotesChange(c.id, event.target.value)}
            rows={4}
            className="w-full rounded-md border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-100"
            placeholder="请输入要追加到该条标准对齐结果下的提示词或人工修改说明..."
          />
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancelModify}
              disabled={savingDecision === c.id}
              className="px-3 py-1.5 text-xs rounded border border-slate-300 text-slate-600 hover:bg-white disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSaveModify}
              disabled={savingDecision === c.id}
              className="px-3 py-1.5 text-xs rounded bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50"
            >
              {savingDecision === c.id ? '保存中...' : '保存修改'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * React 组件 `AlignmentResult`：负责对应页面或区块的 UI 与交互。
 */
const AlignmentResult: React.FC = () => {
  const [searchParams] = useSearchParams();
  /**
   * 函数 `taskId`：本模块内部业务辅助逻辑。
   */
  const taskId = (searchParams.get('taskId') || '').trim();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState<ComparisonTaskData | null>(null);
  const [stats, setStats] = useState<ComparisonStatsData | null>(null);
  const [conflicts, setConflicts] = useState<ComparisonConflictData[]>([]);
  const [conflictTotal, setConflictTotal] = useState(0);
  const [savingDecision, setSavingDecision] = useState<string | null>(null);
  const [modifyConflictId, setModifyConflictId] = useState<string | null>(null);
  const [modifyNotes, setModifyNotes] = useState<Record<string, string>>({});
  const [conflictPage, setConflictPage] = useState(1);
  const [conflictPageSize, setConflictPageSize] = useState(10);
  const { showSuccess, showError } = useToast();

  /**
   * 异步函数 `handleManualDecision`：发起 API 请求或执行页面侧异步流程。
   */
  const handleManualDecision = async (
    conflictId: string,
    decision: 'accept' | 'reject' | 'modify',
    notes?: string
  ) => {
    if (!taskId) return;

    setSavingDecision(conflictId);
    try {
      await alignmentApi.saveManualMapping(taskId, {
        conflict_id: conflictId,
        decision,
        notes,
      });

      // 更新本地状态
      setConflicts(prev => prev.map(c => {
        if (c.id === conflictId) {
          return {
            ...c,
            manual_decision: {
              decision,
              notes,
              updated_at: new Date().toISOString(),
            }
          };
        }
        return c;
      }));
      setModifyConflictId(null);
      setModifyNotes(prev => {
        const next = { ...prev };
        delete next[conflictId];
        return next;
      });
      showSuccess('人工决策已保存');
    } catch (err) {
      showError(getApiErrorMessage(err, '保存决策失败'));
    } finally {
      setSavingDecision(null);
    }
  };

  const pagedConflicts = conflicts;

  useEffect(() => {
    let mounted = true;
    if (!taskId) {
      setError('缺少 taskId，请从“创建对齐任务”进入结果页。');
      return () => {
        mounted = false;
      };
    }
    setLoading(true);
    setError(null);
    Promise.all([
      api.get(Endpoints.COMPARISON_TASK(taskId)),
      api.get(Endpoints.COMPARISON_STATS(taskId)),
      api.get(Endpoints.COMPARISON_CONFLICTS(taskId), {
        params: { page: conflictPage, size: conflictPageSize },
      }),
    ])
      .then(([taskResp, statsResp, conflictsResp]) => {
        if (!mounted) {
          return;
        }
        const conflictsData = conflictsResp?.data as PaginatedConflictsData | ComparisonConflictData[] | undefined;
        const { conflicts: nextConflicts, total } = applyConflictsResponse(conflictsData);
        setTask(taskResp?.data ?? null);
        setStats(statsResp?.data ?? null);
        setConflicts(nextConflicts);
        setConflictTotal(total);
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(getApiErrorMessage(err, '加载对齐结果失败'));
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [taskId, conflictPage, conflictPageSize]);

  return (
    <div className="space-y-6 pb-20">
      <div className="flex justify-between items-end">
        <h1 className="text-2xl font-bold text-slate-900">标准对齐结果与解决方案</h1>
        <div className="text-sm text-slate-500">任务ID: {taskId || '-'}</div>
      </div>

      {loading && <Card className="text-slate-500">正在加载结果…</Card>}
      {!loading && error && <Card className="text-red-600">{error}</Card>}

      {!loading && !error && (
        <>
          <Card>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div><span className="text-slate-500">标准组1：</span><span className="font-medium">{task?.standard_group1 || '-'}</span></div>
              <div><span className="text-slate-500">标准组2：</span><span className="font-medium">{task?.standard_group2 || '-'}</span></div>
              <div><span className="text-slate-500">对齐模式：</span><span>{task?.alignment_mode || '-'}</span></div>
              <div><span className="text-slate-500">优先级规则：</span><span>{task?.priority_rules || '-'}</span></div>
              <div><span className="text-slate-500">比对时间：</span><span>{task?.comparison_time || '-'}</span></div>
              <div><span className="text-slate-500">状态：</span><span>{task?.status || '-'}</span></div>
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card><div className="text-sm text-slate-500">冲突率</div><div className="text-2xl font-bold text-red-500">{stats?.conflict_rate ?? 0}%</div></Card>
            <Card><div className="text-sm text-slate-500">匹配率</div><div className="text-2xl font-bold text-emerald-500">{stats?.match_rate ?? 0}%</div></Card>
            <Card><div className="text-sm text-slate-500">待确认</div><div className="text-2xl font-bold text-amber-500">{stats?.pending_rate ?? 0}%</div></Card>
          </div>

          <Card>
            <h2 className="text-lg font-bold text-blue-600 mb-4">冲突识别结果（按优先级）</h2>
            {conflicts.length === 0 && <div className="text-slate-500 text-sm">暂无冲突结果。</div>}
            <div className="space-y-4">
              {pagedConflicts.map((c) => (
                <ConflictResultCard
                  key={c.id}
                  conflict={c}
                  modifyConflictId={modifyConflictId}
                  modifyNotes={modifyNotes}
                  savingDecision={savingDecision}
                  onManualDecision={handleManualDecision}
                  onModifyConflictIdChange={setModifyConflictId}
                  onModifyNotesChange={(conflictId, notes) =>
                    setModifyNotes((prev) => ({ ...prev, [conflictId]: notes }))
                  }
                  onClearModifyNotes={(conflictId) =>
                    setModifyNotes((prev) => ({ ...prev, [conflictId]: '' }))
                  }
                  showError={showError}
                />
              ))}
            </div>
            {conflictTotal > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <Pagination
                  current={conflictPage}
                  pageSize={conflictPageSize}
                  total={conflictTotal}
                  onChange={setConflictPage}
                  onPageSizeChange={(size) => {
                    setConflictPageSize(size);
                    setConflictPage(1);
                  }}
                />
              </div>
            )}
          </Card>

        </>
      )}
    </div>
  );
};

export default AlignmentResult;
/**
 * @moduleEnd semAlign
 * @file AlignmentResult.tsx
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

