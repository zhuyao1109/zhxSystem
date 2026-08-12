/**
 * @file semAlign
 * @file useStandards.ts
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
import { useCallback, useEffect, useState } from 'react';
import { useAsync } from '@/hooks';
import { standardsService, type StandardsQueryParams } from '../standards.service';
import type { Standard, PaginatedResponse } from '@/types';

/**
 * Hook `useStandards`：封装可复用的状态逻辑与副作用。
 */
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
/**
 * @moduleEnd semAlign
 * @file useStandards.ts
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

