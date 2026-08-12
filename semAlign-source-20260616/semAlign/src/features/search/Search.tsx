import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Sparkles, MessageSquare, BookOpen, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui';
import { HOT_QUERIES, MOCK_SEARCH_RESULTS, SEARCH_SUGGESTIONS } from '@/constants';
import type { SearchMode, SearchResult, SearchSuggestion, Standard } from '@/types';
import { searchApi } from '@/api/modules/search';
import { standardsService } from '@/features/standards/standards.service';
import config from '@/config';
import { getApiErrorMessage } from '@/utils/apiError';

function standardsToSearchRows(standards: Standard[]): SearchResult[] {
  const n = standards.length;
  return standards.map((s, index) => ({
    id: s.id,
    code: s.code,
    title: s.name,
    content: s.description?.trim() ? s.description : `${s.name}（${s.code} ${s.version}）`,
    department: s.department,
    relevance: n <= 1 ? 95 : Math.max(45, Math.round(95 - (index * 50) / Math.max(n - 1, 1))),
  }));
}

const SUGGEST_TYPE_LABELS: Record<string, string> = {
  standard_no: '标准号',
  name: '标准名称',
  category: '分类',
  department: '主管部门',
  source_file: '来源文件',
  history: '历史',
  popular: '热门',
  standard: '标准',
};

function suggestTypeLabel(type: string): string {
  return SUGGEST_TYPE_LABELS[type] ?? type;
}

function renderSearchStatusSummary(
  loading: boolean,
  searchError: string | null,
  totalCount: number
): React.ReactNode {
  if (loading) {
    return '正在检索…';
  }
  if (searchError) {
    return <span className="text-red-500">{searchError}</span>;
  }
  return `找到 ${totalCount} 条相关标准`;
}

function suggestionKey(item: SearchSuggestion): string {
  return `${item.type}-${item.text}`;
}

interface SearchLandingProps {
  query: string;
  searchMode: SearchMode;
  suggestions: SearchSuggestion[];
  suggestOpen: boolean;
  suggestLoading: boolean;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  onSuggestOpen: (open: boolean) => void;
  onSuggestionSelect: (text: string) => void;
  onSearchModeChange: (mode: SearchMode) => void;
  onHotQueryClick: (hotQuery: string) => void;
}

const SearchLanding: React.FC<SearchLandingProps> = ({
  query,
  searchMode,
  suggestions,
  suggestOpen,
  suggestLoading,
  onQueryChange,
  onSearch,
  onSuggestOpen,
  onSuggestionSelect,
  onSearchModeChange,
  onHotQueryClick,
}) => (
  <div className="-m-8 min-h-[calc(100vh+4rem)] flex flex-col items-center justify-center bg-slate-50">
    <div className="text-center max-w-2xl w-full px-4">
      <h1 className="text-4xl font-extrabold text-slate-900 mb-2 tracking-tight">
        新一代标准智能检索
      </h1>
      <p className="text-slate-500 mb-10">
        基于知识图谱与语义模型，精准定位您需要的每一条标准
      </p>

      <div className="relative mb-8">
        <input
          type="text"
          className="w-full h-16 pl-6 pr-32 bg-white text-slate-900 rounded-lg border border-slate-200 shadow-lg text-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="请用一句话描述您的问题或输入关键词/标准号..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          onFocus={() => {
            if (suggestions.length > 0) {
              onSuggestOpen(true);
            }
          }}
          onBlur={() => {
            window.setTimeout(() => onSuggestOpen(false), 150);
          }}
          autoComplete="off"
          aria-expanded={suggestOpen}
          aria-haspopup="listbox"
        />
        {suggestOpen && suggestions.length > 0 && (
          <ul
            className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-20 bg-white border border-slate-200 rounded-lg shadow-xl max-h-72 overflow-y-auto text-left"
            role="listbox"
          >
            {suggestions.map((item) => (
              <li key={suggestionKey(item)} role="option">
                <button
                  type="button"
                  className="w-full px-4 py-3 flex items-center justify-between gap-3 hover:bg-slate-50 text-left border-b border-slate-100 last:border-b-0"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => onSuggestionSelect(item.text)}
                >
                  <span className="text-slate-800 truncate">{item.text}</span>
                  <span className="text-xs text-slate-400 shrink-0">
                    {suggestTypeLabel(item.type)}
                    {item.count != null && item.count > 0 ? ` · ${item.count}` : ''}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {suggestLoading && query.trim().length > 0 && (
          <div className="absolute left-6 top-[calc(100%+0.75rem)] text-xs text-slate-400">
            正在联想…
          </div>
        )}
        <button
          onClick={onSearch}
          className="absolute right-2 top-2 h-12 px-6 rounded-md font-medium transition-colors flex items-center gap-2"
          style={{ backgroundColor: '#2563eb', color: '#ffffff' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#1d4ed8'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#2563eb'; }}
        >
          <Sparkles size={18} />
          智能检索
        </button>
      </div>

      <div className="flex justify-center gap-8 mb-12">
        <button
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => onSearchModeChange('semantic')}
        >
          <div
            className={`w-10 h-6 rounded-full relative transition-colors ${
              searchMode === 'semantic' ? 'bg-blue-600' : 'bg-slate-200'
            }`}
          >
            <div
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${
                searchMode === 'semantic' ? 'right-1' : 'left-1'
              }`}
            />
          </div>
          <span
            className={`text-sm font-bold ${
              searchMode === 'semantic' ? 'text-blue-700' : 'text-slate-500'
            }`}
          >
            语义检索
          </span>
        </button>
        <button
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => onSearchModeChange('exact')}
        >
          <div
            className={`w-10 h-6 rounded-full relative transition-colors ${
              searchMode === 'exact' ? 'bg-blue-600' : 'bg-slate-200'
            }`}
          >
            <div
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${
                searchMode === 'exact' ? 'right-1' : 'left-1'
              }`}
            />
          </div>
          <span
            className={`text-sm ${searchMode === 'exact' ? 'text-blue-700 font-bold' : 'text-slate-500'}`}
          >
            精准匹配
          </span>
        </button>
      </div>

      <div className="space-y-4">
        <p className="text-sm text-slate-400">热门查询示例</p>
        <div className="flex flex-wrap justify-center gap-3">
          {HOT_QUERIES.map((tag) => (
            <button
              key={tag}
              onClick={() => onHotQueryClick(tag)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full text-sm transition-colors"
            >
              {tag}
            </button>
          ))}
        </div>
      </div>
    </div>
  </div>
);

interface StandardDetailModalProps {
  detailLoading: boolean;
  detailError: string | null;
  selectedStandard: Standard | null;
  selectedSearchResult: SearchResult | null;
  onClose: () => void;
}

const StandardDetailModal: React.FC<StandardDetailModalProps> = ({
  detailLoading,
  detailError,
  selectedStandard,
  selectedSearchResult,
  onClose,
}) => (
  <div className="fixed inset-0 z-50 bg-black/35 flex items-center justify-center p-4">
    <div className="w-full max-w-3xl bg-white rounded-lg border border-slate-200 shadow-xl">
      <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900">标准原文详情</h3>
        <button
          className="text-slate-500 hover:text-slate-700 text-sm"
          onClick={onClose}
        >
          关闭
        </button>
      </div>
      <div className="p-5 max-h-[70vh] overflow-y-auto">
        {detailLoading && <p className="text-slate-500">加载中...</p>}
        {!detailLoading && detailError && <p className="text-red-600">{detailError}</p>}
        {!detailLoading && !detailError && selectedStandard && (
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-slate-500">标准编号：</span>
              <span className="font-medium text-slate-900">{selectedStandard.code}</span>
            </div>
            <div>
              <span className="text-slate-500">标准名称：</span>
              <span className="font-medium text-slate-900">{selectedStandard.name}</span>
            </div>
            <div>
              <span className="text-slate-500">版本号：</span>
              <span className="text-slate-900">{selectedStandard.version}</span>
            </div>
            <div>
              <span className="text-slate-500">主管部门：</span>
              <span className="text-slate-900">{selectedStandard.department || '-'}</span>
            </div>
            <div className="pt-2 border-t border-slate-200">
              <div className="text-slate-500 mb-1">原文内容：</div>
              <div className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                {selectedStandard.description?.trim() || '后端暂未保存该标准的详细描述。'}
              </div>
            </div>
          </div>
        )}
        {!detailLoading && !detailError && !selectedStandard && selectedSearchResult && (
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-slate-500">文档标识：</span>
              <span className="font-medium text-slate-900">{selectedSearchResult.code}</span>
            </div>
            <div>
              <span className="text-slate-500">文档名称：</span>
              <span className="font-medium text-slate-900">{selectedSearchResult.title}</span>
            </div>
            <div>
              <span className="text-slate-500">来源：</span>
              <span className="text-slate-900">{selectedSearchResult.department || '-'}</span>
            </div>
            <div className="pt-2 border-t border-slate-200">
              <div className="text-slate-500 mb-1">命中文本片段：</div>
              <div className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                {selectedSearchResult.content?.trim() || '向量库中已命中文档，但暂未返回可展示片段。'}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  </div>
);

const Search: React.FC = () => {
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [query, setQuery] = useState<string>('');
  const [searchMode, setSearchMode] = useState<SearchMode>('semantic');
  const [followUpInput, setFollowUpInput] = useState<string>('');
  const [rawResults, setRawResults] = useState<SearchResult[]>([]);
  const [sortBy, setSortBy] = useState<'relevance' | 'code'>('relevance');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [aiAnswer, setAiAnswer] = useState<string>('');
  const [aiSources, setAiSources] = useState<string[]>([]);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [selectedStandard, setSelectedStandard] = useState<Standard | null>(null);
  const [selectedSearchResult, setSelectedSearchResult] = useState<SearchResult | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [suggestOpen, setSuggestOpen] = useState<boolean>(false);
  const [suggestLoading, setSuggestLoading] = useState<boolean>(false);
  const suggestDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pageSize = 10;

  /** 仅在用户触发检索时调用一次，避免 useEffect 依赖 hasSearched/query 导致重复请求 */
  const fetchSearchResults = useCallback(async (keyword: string): Promise<void> => {
    const q = keyword.trim();
    if (!q) {
      return;
    }
    if (!config.api.useRealApi) {
      setRawResults(MOCK_SEARCH_RESULTS);
      setAiAnswer('');
      setAiSources([]);
      setSearchError(null);
      setCurrentPage(1);
      return;
    }
    setLoading(true);
    setSearchError(null);
    try {
      const res = await searchApi.query(q);
      if (res.code !== 200) {
        setSearchError(res.message || '检索失败');
        setRawResults([]);
        setAiAnswer('');
        setAiSources([]);
        setCurrentPage(1);
        return;
      }
      const mapped = standardsToSearchRows(res.data.standards);
      setRawResults(mapped);
      setAiAnswer((res.data.answer || '').trim());
      setAiSources((res.data.sources || []).filter(Boolean));
      setCurrentPage(1);
    } catch (err: unknown) {
      setSearchError(getApiErrorMessage(err, '检索失败'));
      setRawResults([]);
      setAiAnswer('');
      setAiSources([]);
      setCurrentPage(1);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = useCallback((): void => {
    const q = query.trim();
    if (!q) {
      return;
    }
    setSuggestOpen(false);
    setHasSearched(true);
    fetchSearchResults(q).catch(() => {});
  }, [query, fetchSearchResults]);

  const handleSuggestionSelect = useCallback(
    (text: string): void => {
      const q = text.trim();
      if (!q) {
        return;
      }
      setQuery(q);
      setSuggestOpen(false);
      setHasSearched(true);
      fetchSearchResults(q).catch(() => {});
    },
    [fetchSearchResults]
  );

  useEffect(() => {
    if (hasSearched) {
      setSuggestions([]);
      setSuggestOpen(false);
      return;
    }

    const keyword = query.trim();
    if (!keyword) {
      setSuggestions([]);
      setSuggestOpen(false);
      return;
    }

    if (suggestDebounceRef.current) {
      clearTimeout(suggestDebounceRef.current);
    }

    suggestDebounceRef.current = setTimeout(() => {
      if (!config.api.useRealApi) {
        const mock = SEARCH_SUGGESTIONS.filter((item) =>
          item.text.toLowerCase().includes(keyword.toLowerCase())
        ).slice(0, 8);
        setSuggestions(mock);
        setSuggestOpen(mock.length > 0);
        setSuggestLoading(false);
        return;
      }

      setSuggestLoading(true);
      searchApi
        .getSuggestions(keyword)
        .then((res) => {
          if (res.code === 200) {
            const items = res.data ?? [];
            setSuggestions(items);
            setSuggestOpen(items.length > 0);
          } else {
            setSuggestions([]);
            setSuggestOpen(false);
          }
        })
        .catch(() => {
          setSuggestions([]);
          setSuggestOpen(false);
        })
        .finally(() => {
          setSuggestLoading(false);
        });
    }, 300);

    return () => {
      if (suggestDebounceRef.current) {
        clearTimeout(suggestDebounceRef.current);
      }
    };
  }, [query, hasSearched]);

  const handleHotQueryClick = useCallback(
    (hotQuery: string): void => {
      setQuery(hotQuery);
      setHasSearched(true);
      fetchSearchResults(hotQuery).catch(() => {});
    },
    [fetchSearchResults]
  );

  const handleSearchModeChange = useCallback((mode: SearchMode): void => {
    setSearchMode(mode);
    setCurrentPage(1);
  }, []);

  const handleDetailClose = useCallback((): void => {
    setSelectedStandard(null);
    setSelectedSearchResult(null);
    setDetailError(null);
  }, []);

  const filteredAndSortedResults = useMemo(() => {
    let list = [...rawResults];
    if (searchMode === 'exact') {
      const needle = query.trim().toLowerCase();
      if (needle) {
        list = list.filter((item) =>
          `${item.code} ${item.title} ${item.content}`.toLowerCase().includes(needle)
        );
      }
    }
    if (sortBy === 'code') {
      list.sort((a, b) => a.code.localeCompare(b.code, 'zh-CN'));
    } else {
      list.sort((a, b) => b.relevance - a.relevance);
    }
    return list;
  }, [rawResults, searchMode, sortBy, query]);

  const totalCount = filteredAndSortedResults.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const page = Math.min(currentPage, totalPages);
  const results = filteredAndSortedResults.slice((page - 1) * pageSize, page * pageSize);
  const visiblePages = useMemo(() => {
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + 4);
    const adjustedStart = Math.max(1, end - 4);
    return Array.from({ length: end - adjustedStart + 1 }, (_, i) => adjustedStart + i);
  }, [page, totalPages]);

  const handleFollowUp = useCallback(async (): Promise<void> => {
    const followUp = followUpInput.trim();
    if (!followUp) {
      return;
    }
    setLoading(true);
    try {
      const res = await searchApi.query(followUp);
      if (res.code !== 200) {
        throw new Error(res.message || '追问失败');
      }
      setQuery(followUp);
      setHasSearched(true);
      setRawResults(standardsToSearchRows(res.data.standards || []));
      setAiAnswer((res.data.answer || '').trim());
      setAiSources((res.data.sources || []).filter(Boolean));
      setCurrentPage(1);
      setSearchError(null);
      setFollowUpInput('');
    } catch (err: unknown) {
      setSearchError(getApiErrorMessage(err, '追问失败'));
    } finally {
      setLoading(false);
    }
  }, [followUpInput]);

  const handleViewOriginal = useCallback(async (item: SearchResult): Promise<void> => {
    setDetailLoading(true);
    setDetailError(null);
    setSelectedStandard(null);
    setSelectedSearchResult(null);
    const numericId = Number(item.id);
    const isVectorOnly = (Number.isFinite(numericId) && numericId <= 0) || item.code.startsWith('VECTOR::');
    if (isVectorOnly) {
      setSelectedSearchResult(item);
      setDetailLoading(false);
      return;
    }
    try {
      const detail = await standardsService.getById(item.id);
      setSelectedStandard(detail);
    } catch (err: unknown) {
      setDetailError(getApiErrorMessage(err, '加载标准原文失败'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleViewOriginalClick = useCallback((item: SearchResult): void => {
    handleViewOriginal(item).catch(() => {});
  }, [handleViewOriginal]);

  if (!hasSearched) {
    return (
      <SearchLanding
        query={query}
        searchMode={searchMode}
        suggestions={suggestions}
        suggestOpen={suggestOpen}
        suggestLoading={suggestLoading}
        onQueryChange={setQuery}
        onSearch={handleSearch}
        onSuggestOpen={setSuggestOpen}
        onSuggestionSelect={handleSuggestionSelect}
        onSearchModeChange={handleSearchModeChange}
        onHotQueryClick={handleHotQueryClick}
      />
    );
  }

  // 搜索结果页
  return (
    <div>
      {/* 搜索结果头部 */}
      <div className="mb-6">
        <p className="text-slate-500 mb-2">
          为您找到关于 <span className="text-blue-600 font-bold">"{query}"</span> 的结果
        </p>
        <div className="text-xs text-slate-400">
          {renderSearchStatusSummary(loading, searchError, totalCount)}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* 左侧：AI 问答结果 */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24 border-blue-100 bg-blue-50/50">
            <div className="flex items-center gap-2 mb-4 text-blue-700 font-bold">
              <MessageSquare className="w-5 h-5" /> 智能问答结果
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm text-sm text-slate-700 leading-relaxed mb-4">
              <div className="font-medium mb-2">查询："{query}"</div>
              {aiAnswer ? (
                <p className="mb-4 whitespace-pre-wrap">{aiAnswer}</p>
              ) : (
                <p className="mb-4 text-slate-500">
                  暂无智能问答结果，可输入问题后点击“提交追问”进行补充检索。
                </p>
              )}
              <div className="text-xs text-slate-400 mt-4 pt-4 border-t border-slate-100">
                引用来源：{aiSources.length > 0 ? aiSources.join('，') : '暂无'}
              </div>
            </div>

            {/* 追问输入框 */}
            <div className="relative">
              <input
                className="w-full px-4 py-3 bg-white text-slate-900 rounded-lg border border-slate-200 text-sm focus:ring-1 focus:ring-blue-500 focus:outline-none"
                placeholder="基于以上结果继续追问..."
                value={followUpInput}
                onChange={(e) => setFollowUpInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
              />
              <button
                onClick={handleFollowUp}
                className="absolute right-2 top-2 px-3 py-1.5 rounded text-xs"
                style={{ backgroundColor: '#2563eb', color: '#ffffff' }}
              >
                提交追问
              </button>
            </div>
          </Card>
        </div>

        {/* 右侧：搜索结果列表 */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-800">
              <BookOpen className="w-5 h-5 text-blue-600" /> 相关标准条款
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              排序方式：
              <select
                className="border-none bg-transparent font-medium text-slate-700 focus:ring-0 cursor-pointer"
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value as 'relevance' | 'code');
                  setCurrentPage(1);
                }}
              >
                <option value="relevance">语义相关度</option>
                <option value="code">标准编号</option>
              </select>
            </div>
          </div>

          {loading && (
            <div className="text-center text-slate-500 py-12">加载中…</div>
          )}
          {!loading &&
            results.map((item: SearchResult, index: number) => (
            <Card key={item.id} className="hover:border-blue-300 transition-colors group cursor-pointer">
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm shrink-0">
                  {(page - 1) * pageSize + index + 1}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-blue-600 group-hover:underline">{item.code}</h3>
                    <span className="text-xs text-slate-400">{item.department}</span>
                  </div>
                  <p className="text-slate-800 font-medium mb-2">{item.title}</p>
                  <p className="text-slate-600 text-sm mb-2">{item.content}</p>

                  {/* 相关度指示器 */}
                  <div className="flex items-center gap-4 mt-4">
                    <div className="flex-1 bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-green-500 h-full rounded-full"
                        style={{ width: `${item.relevance}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-slate-500">
                      语义相关度: {item.relevance}%
                    </span>
                  </div>

                  <button
                    className="text-blue-600 text-sm mt-4 hover:underline flex items-center gap-1"
                    onClick={() => handleViewOriginalClick(item)}
                  >
                    查看原文 <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
          {!loading && results.length === 0 && !searchError && (
            <p className="text-slate-500 text-center py-8">暂无结果，请尝试其他关键词</p>
          )}

          {/* 分页 */}
          {totalCount > 0 && (
            <div className="flex justify-center mt-8">
              <div className="flex border border-slate-200 rounded-md bg-white">
                <button
                  className="px-3 py-2 border-r border-slate-200 hover:bg-slate-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={page <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  &lt;
                </button>
                {visiblePages.map((pageNo) => (
                  <button
                    key={pageNo}
                    className={`px-4 py-2 ${pageNo === page ? 'font-medium' : 'hover:bg-slate-50 text-slate-600'}`}
                    style={pageNo === page ? { backgroundColor: '#eff6ff', color: '#2563eb' } : undefined}
                    onClick={() => setCurrentPage(pageNo)}
                  >
                    {pageNo}
                  </button>
                ))}
                <button
                  className="px-3 py-2 border-l border-slate-200 hover:bg-slate-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={page >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                >
                  &gt;
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {(detailLoading || detailError || selectedStandard || selectedSearchResult) && (
        <StandardDetailModal
          detailLoading={detailLoading}
          detailError={detailError}
          selectedStandard={selectedStandard}
          selectedSearchResult={selectedSearchResult}
          onClose={handleDetailClose}
        />
      )}
    </div>
  );
};

export default Search;
