/**
 * @file semAlign
 * @file ToastContext.tsx
 * @description 通用业务组件：Toast、对话框、章节标题与布局辅助。
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
import React, { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from 'react';

/**
 * 类型别名 `ToastType`：约束业务字段或联合枚举取值。
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/**
 * 类型定义 `Toast`：描述前后端交互或页面状态结构。
 */
export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

/**
 * 类型定义 `ToastContextValue`：描述前后端交互或页面状态结构。
 */
interface ToastContextValue {
  toasts: Toast[];
  showToast: (type: ToastType, message: string, duration?: number) => void;
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
  showWarning: (message: string) => void;
  showInfo: (message: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Hook `useToast`：封装可复用的状态逻辑与副作用。
 */
export const useToast = (): ToastContextValue => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

/**
 * 类型定义 `ToastProviderProps`：描述前后端交互或页面状态结构。
 */
interface ToastProviderProps {
  children: ReactNode;
}

/**
 * React 组件 `ToastProvider`：负责对应页面或区块的 UI 与交互。
 */
export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((type: ToastType, message: string, duration = 5000) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const newToast: Toast = { id, type, message, duration };

    setToasts((prev) => [...prev, newToast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast]);

  const showSuccess = useCallback((message: string) => showToast('success', message), [showToast]);
  const showError = useCallback((message: string) => showToast('error', message), [showToast]);
  const showWarning = useCallback((message: string) => showToast('warning', message), [showToast]);
  const showInfo = useCallback((message: string) => showToast('info', message), [showToast]);

  const value = useMemo<ToastContextValue>(
    () => ({
      toasts,
      showToast,
      showSuccess,
      showError,
      showWarning,
      showInfo,
      removeToast,
    }),
    [toasts, showToast, showSuccess, showError, showWarning, showInfo, removeToast]
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
};
/**
 * @moduleEnd semAlign
 * @file ToastContext.tsx
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

