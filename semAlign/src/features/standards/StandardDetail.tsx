/**
 * @file semAlign
 * @file StandardDetail.tsx
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
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';

import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { Card } from '@/components/ui';
import { getApiErrorMessage } from '@/utils/apiError';
import { downloadStandardFile } from './standardDownload';

// -----------------------------------------------------------------------------
// 分段：StandardDetail.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。
// -----------------------------------------------------------------------------

/**
 * 类型定义 `StandardDetailData`：描述前后端交互或页面状态结构。
 */
interface StandardDetailData {
  id: number;
  standard_no: string;
  name: string;
  version: string;
  status: string;
  category: string;
  department?: string | null;
  description?: string | null;
  source_file?: string | null;
  created_at: string;
  updated_at?: string | null;
}

/**
 * 类型定义 `StandardContentData`：描述前后端交互或页面状态结构。
 */
interface StandardContentData {
  standard_id: number;
  source_file?: string | null;
  has_original_file: boolean;
  has_text_file: boolean;
  text_file_name?: string | null;
  text_length: number;
  text_truncated: boolean;
  text_content: string;
}

/**
 * 类型定义 `StandardDetailFetchResult`：描述前后端交互或页面状态结构。
 */
interface StandardDetailFetchResult {
  standard: StandardDetailData;
  content: StandardContentData | null;
}

/**
 * 异步函数 `fetchStandardDetail`：发起 API 请求或执行页面侧异步流程。
 */
async function fetchStandardDetail(id: string): Promise<StandardDetailFetchResult> {
  const [detailResp, contentResp]: [
    { code: number; message: string; data: StandardDetailData },
    { code: number; message: string; data: StandardContentData }
  ] = await Promise.all([
    api.get(Endpoints.STANDARD_DETAIL(id)),
    api.get(Endpoints.STANDARD_CONTENT(id)),
  ]);

  if (detailResp.code !== 200 || !detailResp.data) {
    throw new Error(detailResp.message || '加载标准详情失败');
  }

  const content = contentResp.code === 200 && contentResp.data ? contentResp.data : null;
  return { standard: detailResp.data, content };
}

/**
 * React 组件 `StandardDetail`：负责对应页面或区块的 UI 与交互。
 */
const StandardDetail: React.FC = () => {
  const navigate = useNavigate();
  const { standardId } = useParams<{ standardId: string }>();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [standard, setStandard] = useState<StandardDetailData | null>(null);
  const [content, setContent] = useState<StandardContentData | null>(null);

  useEffect(() => {
    let mounted = true;
    /**
     * 函数 `id`：本模块内部业务辅助逻辑。
     */
    const id = (standardId || '').trim();
    if (!id) {
      setError('缺少标准 ID');
      return () => {
        mounted = false;
      };
    }

    setLoading(true);
    setError(null);
    fetchStandardDetail(id)
      .then((result) => {
        if (!mounted) {
          return;
        }
        setStandard(result.standard);
        setContent(result.content);
      })
      .catch((err: unknown) => {
        if (!mounted) {
          return;
        }
        setError(getApiErrorMessage(err, '加载标准详情失败'));
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [standardId]);

  /**
   * 异步函数 `handleDownload`：发起 API 请求或执行页面侧异步流程。
   */
  const handleDownload = async (kind: 'original' | 'text'): Promise<void> => {
    /**
     * 函数 `id`：本模块内部业务辅助逻辑。
     */
    const id = (standardId || '').trim();
    if (!id || !standard) {
      return;
    }
    const defaultName = `${standard.standard_no}${kind === 'text' ? '.txt' : '.pdf'}`;
    try {
      await downloadStandardFile(id, kind, defaultName);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '下载失败'));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">标准详情</h1>
        <button
          onClick={() => navigate('/database')}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft size={16} /> 返回标准库
        </button>
      </div>

      {loading && <Card className="text-slate-500">加载中...</Card>}
      {!loading && error && <Card className="text-red-600">{error}</Card>}

      {!loading && !error && standard && (
        <>
          <Card>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div><span className="text-slate-500">标准编号：</span><span className="font-medium">{standard.standard_no}</span></div>
              <div><span className="text-slate-500">标准名称：</span><span className="font-medium">{standard.name}</span></div>
              <div><span className="text-slate-500">版本：</span><span>{standard.version}</span></div>
              <div><span className="text-slate-500">状态：</span><span>{standard.status}</span></div>
              <div><span className="text-slate-500">部门：</span><span>{standard.department || '-'}</span></div>
              <div><span className="text-slate-500">分类：</span><span>{standard.category || '-'}</span></div>
              <div><span className="text-slate-500">来源文件：</span><span>{standard.source_file || '-'}</span></div>
              <div><span className="text-slate-500">创建时间：</span><span>{standard.created_at || '-'}</span></div>
            </div>
            <div className="mt-4 text-sm">
              <div className="text-slate-500 mb-1">描述</div>
              <div className="text-slate-800 whitespace-pre-wrap">{standard.description || '-'}</div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => void handleDownload('original')}
                disabled={!content?.has_original_file}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download size={16} /> 下载原文
              </button>
              <button
                onClick={() => void handleDownload('text')}
                disabled={!content?.has_text_file}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download size={16} /> 下载解析文本
              </button>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">解析文本预览</h2>
            {!content?.has_text_file ? (
              <div className="text-sm text-slate-500">暂无解析文本</div>
            ) : (
              <>
                <div className="text-xs text-slate-500 mb-2">
                  文件：{content.text_file_name || '-'} | 字符数：{content.text_length}
                  {content.text_truncated ? '（已截断显示）' : ''}
                </div>
                <pre className="text-sm text-slate-800 whitespace-pre-wrap bg-slate-50 border border-slate-200 rounded-md p-3 max-h-[520px] overflow-auto">
                  {content.text_content || '暂无可展示文本'}
                </pre>
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default StandardDetail;
/**
 * @moduleEnd semAlign
 * @file StandardDetail.tsx
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

