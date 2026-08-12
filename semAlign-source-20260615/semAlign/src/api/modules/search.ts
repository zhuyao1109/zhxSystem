/**
 * 智能检索 API 模块
 *
 * 提供智能搜索和搜索建议功能
 */

import apiAdapter from '@/api/adapter';
import type { ApiResponse, SearchQueryData, SearchQueryOptions, SearchSuggestion } from '@/types';

export const searchApi = {
  /**
   * 搜索标准
   */
  query: async (keyword: string, options?: SearchQueryOptions): Promise<ApiResponse<SearchQueryData>> => {
    return apiAdapter.search.query(keyword, options);
  },

  /**
   * 获取搜索建议
   */
  getSuggestions: async (keyword?: string): Promise<ApiResponse<SearchSuggestion[]>> => {
    return apiAdapter.search.getSuggestions(keyword);
  },
};

export default searchApi;
