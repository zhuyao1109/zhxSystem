import { useEffect, useCallback } from 'react';
import { useAsync } from '@/hooks';
import { workbenchService } from '../workbench.service';
import type { WorkbenchData } from '@/types';

export function useWorkbench() {
  const { data, loading, error, execute } = useAsync<WorkbenchData>();

  const fetchData = useCallback(async () => {
    return execute(() => workbenchService.getDashboardData());
  }, [execute]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

export default useWorkbench;
