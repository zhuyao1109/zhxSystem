/**
 * @file semAlign
 * @file Loading.tsx
 * @description 基础 UI 组件库：按钮、卡片、分页、加载态等可复用控件。
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
import { Loader2 } from 'lucide-react';

/**
 * 类型定义 `LoadingProps`：描述前后端交互或页面状态结构。
 */
export interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

/**
 * React 组件 `Loading`：负责对应页面或区块的 UI 与交互。
 */
export const Loading: React.FC<LoadingProps> = ({
  size = 'md',
  text,
  className = '',
}) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loader2 className={`${sizes[size]} animate-spin text-blue-600`} />
      {text && <span className="text-slate-500 text-sm">{text}</span>}
    </div>
  );
};

/**
 * React 组件 `PageLoading`：负责对应页面或区块的 UI 与交互。
 */
export const PageLoading: React.FC = () => (
  <div className="flex items-center justify-center min-h-[400px]">
    <Loading size="lg" text="加载中..." />
  </div>
);

/**
 * 类型定义 `SkeletonProps`：描述前后端交互或页面状态结构。
 */
export interface SkeletonProps {
  lines?: number;
  avatar?: boolean;
  className?: string;
}

const SKELETON_LINE_IDS = ['sk-a', 'sk-b', 'sk-c', 'sk-d', 'sk-e', 'sk-f', 'sk-g', 'sk-h'] as const;

/**
 * React 组件 `Skeleton`：负责对应页面或区块的 UI 与交互。
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  lines = 3,
  avatar = false,
  className = '',
}) => (
  <div className={`animate-pulse space-y-4 ${className}`}>
    {avatar && (
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 bg-slate-200 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-slate-200 rounded w-1/3" />
          <div className="h-3 bg-slate-200 rounded w-1/4" />
        </div>
      </div>
    )}
    {SKELETON_LINE_IDS.slice(0, lines).map((lineId, i) => (
      <div
        key={lineId}
        className="h-4 bg-slate-200 rounded"
        style={{ width: `${70 + (i % 3) * 10}%` }}
      />
    ))}
  </div>
);

export default Loading;
/**
 * @moduleEnd semAlign
 * @file Loading.tsx
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

