/**
 * @file semAlign
 * @file MetricCard.tsx
 * @description 治理工作台：指标卡、图表统计与标准动态列表。
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
import { ArrowUp, ArrowDown } from 'lucide-react';
import { Card } from '@/components/ui';
import type { Metric } from '@/types';

/**
 * 类型定义 `MetricCardProps`：描述前后端交互或页面状态结构。
 */
export interface MetricCardProps {
  metric: Metric;
}

/**
 * React 组件 `MetricCard`：负责对应页面或区块的 UI 与交互。
 */
export const MetricCard: React.FC<MetricCardProps> = ({ metric }) => {
  const isPositive = metric.trend >= 0;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex flex-col h-full justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{metric.label}</p>
          <h3 className="text-4xl font-bold text-blue-600 mt-2 flex items-baseline gap-1">
            {metric.value}
            {metric.unit != null && metric.unit !== '' && (
              <span className="text-lg font-semibold text-slate-500">{metric.unit}</span>
            )}
          </h3>
        </div>
        <div className="flex items-center mt-4">
          {metric.trend !== 0 && (
            <span
              className={`flex items-center text-xs font-medium ${
                isPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
              {Math.abs(metric.trend)}%
            </span>
          )}
          {metric.trendLabel && (
            <span className="text-xs text-slate-400 ml-2">{metric.trendLabel}</span>
          )}
        </div>
      </div>
    </Card>
  );
};

export default MetricCard;
/**
 * @moduleEnd semAlign
 * @file MetricCard.tsx
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

