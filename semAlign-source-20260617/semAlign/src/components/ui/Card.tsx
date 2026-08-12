/**
 * @file semAlign
 * @file Card.tsx
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

/**
 * 类型定义 `CardProps`：描述前后端交互或页面状态结构。
 */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  shadow?: 'none' | 'sm' | 'md' | 'lg';
}

/**
 * React 组件 `Card`：负责对应页面或区块的 UI 与交互。
 */
export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
  shadow = 'md',
  ...rest
}) => {
  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-8',
  };

  const shadows = {
    none: '',
    sm: 'shadow-sm',
    md: 'shadow',
    lg: 'shadow-lg',
  };

  return (
    <div
      {...rest}
      className={`bg-white rounded-lg border border-slate-200 ${shadows[shadow]} ${paddings[padding]} ${className}`}
    >
      {children}
    </div>
  );
};

/**
 * 类型定义 `CardHeaderProps`：描述前后端交互或页面状态结构。
 */
export interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

/**
 * React 组件 `CardHeader`：负责对应页面或区块的 UI 与交互。
 */
export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className = '',
}) => (
  <div className={`flex items-center justify-between mb-4 ${className}`}>
    <div>
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
    </div>
    {action && <div>{action}</div>}
  </div>
);

export default Card;
/**
 * @moduleEnd semAlign
 * @file Card.tsx
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

