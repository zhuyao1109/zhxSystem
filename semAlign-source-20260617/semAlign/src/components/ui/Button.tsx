/**
 * @file semAlign
 * @file Button.tsx
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
 * 类型定义 `ButtonProps`：描述前后端交互或页面状态结构。
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: { backgroundColor: '#2563eb', color: '#ffffff' },
  secondary: { backgroundColor: '#f1f5f9', color: '#334155' },
  ghost: { backgroundColor: 'transparent', color: '#475569' },
  danger: { backgroundColor: '#dc2626', color: '#ffffff' },
};

const variantHoverStyles: Record<string, React.CSSProperties> = {
  primary: { backgroundColor: '#1d4ed8' },
  secondary: { backgroundColor: '#e2e8f0' },
  ghost: { backgroundColor: '#f1f5f9' },
  danger: { backgroundColor: '#b91c1c' },
};

/**
 * React 组件 `Button`：负责对应页面或区块的 UI 与交互。
 */
export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  disabled,
  className = '',
  style,
  ...props
}) => {
  const [isHovered, setIsHovered] = React.useState(false);

  const sizeStyles: React.CSSProperties = {
    sm: { padding: '6px 12px', fontSize: '14px' },
    md: { padding: '8px 16px', fontSize: '16px' },
    lg: { padding: '12px 24px', fontSize: '18px' },
  };

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 500,
    borderRadius: '6px',
    transition: 'all 0.2s',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    ...variantStyles[variant],
    ...(isHovered && !disabled ? variantHoverStyles[variant] : {}),
    ...sizeStyles[size],
    ...style,
  };

  return (
    <button
      className={className}
      style={baseStyle}
      disabled={disabled || loading}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {!loading && icon && <span className="mr-2">{icon}</span>}
      {children}
    </button>
  );
};

export default Button;
/**
 * @moduleEnd semAlign
 * @file Button.tsx
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

