import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';

import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import { Card } from '@/components/ui';
import { getApiErrorMessage } from '@/utils/apiError';
import { downloadStandardFile } from './standardDownload';

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

interface StandardDetailFetchResult {
  standard: StandardDetailData;
  content: StandardContentData | null;
}

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

const StandardDetail: React.FC = () => {
  const navigate = useNavigate();
  const { standardId } = useParams<{ standardId: string }>();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [standard, setStandard] = useState<StandardDetailData | null>(null);
  const [content, setContent] = useState<StandardContentData | null>(null);

  useEffect(() => {
    let mounted = true;
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

  const handleDownload = async (kind: 'original' | 'text'): Promise<void> => {
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
