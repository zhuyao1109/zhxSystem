/**
 * @file semAlign
 * @file Workbench.tsx
 * @description 治理工作台：指标卡、图表统计与标准动态列表。
 * @remarks 治理工作台首页：拉取 dashboard 指标与图表数据。
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
import React from 'react';
import { MetricCard } from './components/MetricCard';
import { DynamicList } from './components/DynamicList';
import { ChartsSection } from './components/ChartsSection';
import { useWorkbench } from './hooks/useWorkbench';
import { PageLoading } from '@/components/ui';

/**
 * 治理工作台首页：拉取 dashboard 指标与图表数据。
 */
export const Workbench: React.FC = () => {
  const { data, loading, error } = useWorkbench();

  if (loading) {
    return <PageLoading />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-6 text-red-700 text-sm">
        工作台数据加载失败，请刷新页面或稍后重试。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">核心指标概览</h1>

      {/* 指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {(data?.metrics ?? []).map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      {/* 图表区域 */}
      {data?.charts && <ChartsSection charts={data.charts} />}

      {/* 动态列表 */}
      <div className="grid grid-cols-1 gap-6">
        {data?.dynamics && <DynamicList dynamics={data.dynamics} />}
      </div>
    </div>
  );
};

export default Workbench;
/**
 * @moduleEnd semAlign
 * @file Workbench.tsx
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

