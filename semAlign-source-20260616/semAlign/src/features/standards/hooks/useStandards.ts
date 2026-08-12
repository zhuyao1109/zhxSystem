import { useCallback, useEffect, useState } from 'react';
import { useAsync } from '@/hooks';
import { standardsService, type StandardsQueryParams } from '../standards.service';
import type { Standard, PaginatedResponse } from '@/types';

export function useStandards(initialParams?: StandardsQueryParams) {
  const [params, setParams] = useState<StandardsQueryParams>({
    page: 1,
    size: 10,
    ...initialParams,
  });

  const { data, loading, error, execute } = useAsync<PaginatedResponse<Standard>>();

  const fetchList = useCallback(async (newParams?: StandardsQueryParams) => {
    const finalParams = newParams || params;
    return execute(() => standardsService.getList(finalParams));
  }, [params, execute]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const search = useCallback((keyword: string) => {
    setParams((prev) => ({ ...prev, keyword, page: 1 }));
  }, []);

  const filter = useCallback((filters: Partial<StandardsQueryParams>) => {
    setParams((prev) => ({ ...prev, ...filters, page: 1 }));
  }, []);

  const setPage = useCallback((page: number) => {
    setParams((prev) => ({ ...prev, page }));
  }, []);

  const reset = useCallback(() => {
    setParams({ page: 1, size: 10 });
  }, []);

  return {
    standards: data?.data || [],
    pagination: data
      ? {
          current: data.page,
          pageSize: data.size,
          total: data.total,
          totalPages: Math.ceil(data.total / data.size),
        }
      : null,
    loading,
    error,
    params,
    setParams,
    search,
    filter,
    setPage,
    reset,
    refetch: fetchList,
  };
}

export default useStandards;
