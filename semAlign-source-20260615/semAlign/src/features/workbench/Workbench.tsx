import React from 'react';
import { MetricCard } from './components/MetricCard';
import { DynamicList } from './components/DynamicList';
import { ChartsSection } from './components/ChartsSection';
import { useWorkbench } from './hooks/useWorkbench';
import { PageLoading } from '@/components/ui';

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
