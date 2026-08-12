import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Bot, Send, User, RotateCcw, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { SectionTitle, useToast } from '@/components/common';
import { getApiErrorMessage } from '@/utils/apiError';
import { Card, Button } from '@/components/ui';
import { PRIORITY_RULES } from '@/constants';
import { alignmentService } from './alignment.service';
import { standardsService } from '@/features/standards/standards.service';
import api from '@/api/axios';
import { Endpoints } from '@/api/endpoints';
import type { AlignmentMessage, PriorityRule, Standard } from '@/types';

interface VectorSourceRow {
  source: string;
  saved_as?: string | null;
  chunk_count: number;
}

interface VectorStoreOverviewData {
  available: boolean;
  db_path: string;
  rows: VectorSourceRow[];
}

interface AlignmentTaskDetailData {
  id?: number;
  status?: string;
  result_json?: Record<string, unknown> | null;
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => window.setTimeout(resolve, ms));

function vectorRowToStandard(row: VectorSourceRow): Standard {
  const source = (row.source || '').trim();
  return {
    id: `vector:${source}`,
    code: `VECTOR::${source}`,
    name: source,
    version: '-',
    status: 'new',
    department: '向量库',
    date: new Date().toISOString().slice(0, 10),
    category: '向量文档',
    description: `向量库来源文档，chunk 数：${row.chunk_count}`,
  };
}

async function fetchAllStandardsPages(pageSize = 100): Promise<Standard[]> {
  const first = await standardsService.getList({ page: 1, size: pageSize });
  let all = first.data ?? [];
  const total = first.total ?? all.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  for (let p = 2; p <= totalPages; p += 1) {
    const next = await standardsService.getList({ page: p, size: pageSize });
    all = all.concat(next.data ?? []);
  }
  return all;
}

async function fetchVectorSourceRows(): Promise<VectorSourceRow[]> {
  try {
    const vectorResp: {
      code: number;
      message: string;
      data: VectorStoreOverviewData;
    } = await api.get(Endpoints.VECTOR_STORE_OVERVIEW);
    if (vectorResp.code === 200 && vectorResp.data?.available) {
      return vectorResp.data.rows ?? [];
    }
  } catch {
    // 向量库读取失败不影响标准库下拉
  }
  return [];
}

async function loadStandardsForAlignment(): Promise<Standard[]> {
  const all = await fetchAllStandardsPages();
  const vectorRows = await fetchVectorSourceRows();
  const vectorCandidates = vectorRows
    .filter((r) => (r.source || '').trim().length > 0)
    .map(vectorRowToStandard);
  return [...all, ...vectorCandidates];
}

const Alignment: React.FC = () => {
  const navigate = useNavigate();
  const { showSuccess, showError, showWarning } = useToast();
  const [messages, setMessages] = useState<AlignmentMessage[]>([
    {
      id: '1',
      type: 'ai',
      content: `您好！我是标准对齐助手，可以帮助您：
• 分析标准之间的潜在冲突
• 解释标准条款的含义
• 提供对齐策略建议
• 回答关于标准对齐的问题

请选择标准组后与我交流！`,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState<string>('');
  const [selectedGroup1, setSelectedGroup1] = useState<string>('');
  const [selectedGroup2, setSelectedGroup2] = useState<string>('');
  const [priorityRules, setPriorityRules] = useState<PriorityRule[]>(PRIORITY_RULES);
  const [customRule, setCustomRule] = useState<string>('');
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [standardsLoading, setStandardsLoading] = useState<boolean>(false);
  const [creatingTask, setCreatingTask] = useState<boolean>(false);
  const [taskProgressText, setTaskProgressText] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback((): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    let mounted = true;
    setStandardsLoading(true);
    loadStandardsForAlignment()
      .then((merged) => {
        if (mounted) {
          setStandards(merged);
        }
      })
      .catch((error) => {
        if (mounted) {
          showError(getApiErrorMessage(error, '加载标准库失败，请先确认已导入标准'));
        }
      })
      .finally(() => {
        if (mounted) {
          setStandardsLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [showError]);

  const handleSend = useCallback(async (): Promise<void> => {
    const question = inputValue.trim();
    if (!question) return;

    const newUserMessage: AlignmentMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInputValue('');
    setChatLoading(true);
    try {
      const response = await alignmentService.chat({
        message: question,
        group1Id: selectedGroup1 || undefined,
        group2Id: selectedGroup2 || undefined,
      });
      const aiResponse: AlignmentMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: response.data?.answer || '已收到问题，但暂时没有可用回复。',
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error('发送聊天消息失败:', error);
      showError(getApiErrorMessage(error, '发送失败，请稍后重试'));
    } finally {
      setChatLoading(false);
    }
  }, [inputValue, selectedGroup1, selectedGroup2, showError]);

  const handleQuickQuestion = useCallback((question: string): void => {
    setInputValue(question);
  }, []);

  const handleRuleChange = useCallback((ruleId: string): void => {
    setPriorityRules((prev) =>
      prev.map((rule) => (rule.id === ruleId ? { ...rule, checked: !rule.checked } : rule))
    );
  }, []);

  const waitForTaskCompletion = useCallback(async (taskId: string): Promise<void> => {
    const maxAttempts = 120;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const resp = await alignmentService.getTaskDetail(taskId);
      const task = resp.data as AlignmentTaskDetailData | undefined;
      const status = task?.status || 'pending';

      if (status === 'completed') {
        setTaskProgressText('对齐完成，正在打开结果页...');
        return;
      }
      if (status === 'failed') {
        const error = task?.result_json?.error;
        throw new Error(typeof error === 'string' ? error : '对齐任务执行失败');
      }

      setTaskProgressText(status === 'processing' ? '正在执行标准对齐，请稍候...' : '任务已提交，等待后台处理...');
      await sleep(attempt < 10 ? 1000 : 2000);
    }
    throw new Error('对齐任务仍在处理中，请稍后到任务列表查看结果');
  }, []);

  const handleCreateTask = useCallback(async () => {
    if (!selectedGroup1 || !selectedGroup2) {
      showWarning('请选择两个标准组');
      return;
    }
    if (selectedGroup1 === selectedGroup2) {
      showWarning('请选择两个不同的标准');
      return;
    }

    const left = standards.find((item) => item.id === selectedGroup1);
    const right = standards.find((item) => item.id === selectedGroup2);
    if (!left || !right) {
      showWarning('请选择数据库中存在的标准');
      return;
    }

    try {
      setCreatingTask(true);
      setTaskProgressText('正在创建对齐任务...');
      const selectedRules = priorityRules.filter((r) => r.checked).map((r) => r.id);
      const resp = await alignmentService.createTask({
        group1Id: selectedGroup1,
        group2Id: selectedGroup2,
        group1Name: `${left.code} ${left.name}`,
        group2Name: `${right.code} ${right.name}`,
        priorityRules: selectedRules,
        customRule: customRule || undefined,
      });
      let taskId = resp?.data?.taskId;
      if (!taskId) {
        const listResp = await alignmentService.getTaskList();
        taskId = listResp?.data?.[0]?.taskId;
      }
      if (!taskId) {
        throw new Error('任务已创建，但未获取到任务ID');
      }
      showSuccess('对齐任务创建成功，正在自动等待结果...');
      await waitForTaskCompletion(taskId);
      showSuccess('对齐任务已完成！');
      navigate(`/alignment/result?taskId=${encodeURIComponent(taskId)}`);
    } catch (error) {
      console.error('创建对齐任务失败:', error);
      showError(getApiErrorMessage(error, '创建对齐任务失败，请重试'));
    } finally {
      setCreatingTask(false);
      setTaskProgressText('');
    }
  }, [selectedGroup1, selectedGroup2, standards, priorityRules, customRule, showSuccess, showError, showWarning, navigate, waitForTaskCompletion]);

  const handleCancel = useCallback((): void => {
    setSelectedGroup1('');
    setSelectedGroup2('');
    setCustomRule('');
    setInputValue('');
    setPriorityRules(PRIORITY_RULES.map((rule) => ({ ...rule })));
  }, []);

  const handleViewHistory = useCallback((): void => {
    navigate('/alignment/tasks');
  }, [navigate]);

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>): void => {
      if (e.key === 'Enter') {
        handleSend().catch(() => {});
      }
    },
    [handleSend]
  );

  const handleSendClick = useCallback((): void => {
    handleSend().catch(() => {});
  }, [handleSend]);

  const quickQuestions = ['这两个标准的主要差异是什么?', '如何设置优先级规则?', '解释难点条款'];

  return (
    <div>
      <SectionTitle title="创建对齐任务" />

      {/* 选择标准组 */}
      <Card className="mb-6">
        <h3 className="font-bold text-blue-600 mb-4">选择待对齐标准组</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">标准组 1</label>
            <select
              className="w-full bg-white text-slate-900 border-slate-300 rounded-md shadow-sm border p-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedGroup1}
              onChange={(e) => setSelectedGroup1(e.target.value)}
            >
              <option value="">{standardsLoading ? '加载中...' : '请选择标准'}</option>
              {standards.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} {item.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">标准组 2</label>
            <select
              className="w-full bg-white text-slate-900 border-slate-300 rounded-md shadow-sm border p-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedGroup2}
              onChange={(e) => setSelectedGroup2(e.target.value)}
            >
              <option value="">{standardsLoading ? '加载中...' : '请选择标准'}</option>
              {standards.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} {item.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-500">
          提示：可选择标准库记录或向量库已入库文档进行对齐
        </p>
        {!standardsLoading && standards.length < 2 && (
          <p className="mt-2 text-xs text-amber-700">
            当前标准库不足 2 条，请先到“标准导入”页面提交文件并完成导入。
          </p>
        )}
      </Card>

      {/* 主内容区：AI 助手 + 设置 */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* 左侧：AI 助手 */}
        <div className="flex-1 flex flex-col h-[600px] bg-white rounded-lg border border-slate-200 shadow-sm">
          <div className="p-4 border-b border-slate-200 bg-blue-600 text-white rounded-t-lg flex justify-between items-center">
            <div className="font-bold flex items-center gap-2">
              <Bot size={20} /> 标准对齐助手{' '}
              <span className="text-xs bg-blue-500 px-2 py-0.5 rounded text-blue-100">在线</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-slate-50">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.type === 'user' ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
                    msg.type === 'ai' ? 'bg-green-500 text-white' : 'bg-slate-300 text-slate-600'
                  }`}
                >
                  {msg.type === 'ai' ? 'AI' : <User size={16} />}
                </div>
                <div
                  className={`max-w-[80%] rounded-lg p-3 text-sm shadow-sm whitespace-pre-wrap ${
                    msg.type === 'ai' ? 'bg-white text-slate-800' : 'bg-blue-600 text-white'
                  }`}
                >
                  {msg.content}
                  <div
                    className={`text-xs mt-2 text-right ${
                      msg.type === 'ai' ? 'text-slate-400' : 'text-blue-200'
                    }`}
                  >
                    {msg.timestamp}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 bg-white border-t border-slate-200">
            <div className="flex gap-2 mb-3 overflow-x-auto pb-2">
              {quickQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => handleQuickQuestion(q)}
                  className="whitespace-nowrap px-3 py-1 bg-slate-100 hover:bg-slate-200 text-xs text-slate-600 rounded-full border border-slate-200 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 bg-white text-slate-900 border border-slate-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="输入您的问题..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleInputKeyDown}
              />
              <button
                onClick={handleSendClick}
                disabled={chatLoading}
                className="bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：设置 */}
        <div className="lg:w-1/3 space-y-6">
          <Card>
            <h3 className="font-bold text-blue-600 mb-4">设置对齐优先级规则</h3>
            <div className="space-y-3">
              {priorityRules.map((rule) => (
                <label
                  key={rule.id}
                  className="flex items-center space-x-3 cursor-pointer p-2 hover:bg-slate-50 rounded"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                    checked={rule.checked}
                    onChange={() => handleRuleChange(rule.id)}
                  />
                  <span className="text-sm text-slate-700">{rule.label}</span>
                </label>
              ))}
            </div>

            <div className="mt-6">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                自定义优先级规则
              </label>
              <textarea
                className="w-full bg-white text-slate-900 border border-slate-300 rounded-md p-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="输入自定义优先级规则（可选）"
                rows={3}
                value={customRule}
                onChange={(e) => setCustomRule(e.target.value)}
              />
            </div>
          </Card>

          {creatingTask && taskProgressText && (
            <Card className="bg-amber-50 border-amber-100">
              <div className="flex items-center gap-3 text-sm text-amber-800">
                <Loader2 size={18} className="animate-spin text-amber-600" />
                <span>{taskProgressText}</span>
              </div>
              <p className="text-xs text-amber-700 mt-2">
                页面会在任务完成后自动打开对齐结果，请不要重复点击创建。
              </p>
            </Card>
          )}

          <div className="flex gap-4">
            <Button variant="secondary" className="flex-1" onClick={handleCancel} disabled={creatingTask}>
              取消
            </Button>
            <Button className="flex-1" onClick={handleCreateTask} disabled={creatingTask}>
              {creatingTask ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin" /> 对齐中
                </span>
              ) : (
                '创建对齐任务'
              )}
            </Button>
          </div>

          <Card
            className="bg-blue-50 border-blue-100 cursor-pointer hover:bg-blue-100/60 transition-colors"
            onClick={handleViewHistory}
          >
            <div className="flex gap-3">
                <RotateCcw className="text-blue-500 mt-1" size={20} />
              <div>
                <h4 className="text-sm font-bold text-blue-800">查看任务列表管理</h4>
                <p className="text-xs text-blue-600 mt-1">
                  查看历史任务、任务状态，并支持删除不再需要的任务。
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Alignment;
