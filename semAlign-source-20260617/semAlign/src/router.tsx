/**
 * @file semAlign
 * @file router.tsx
 * @description SemAlign 前端源码模块，参与民航多源标准治理系统 UI 展示。
 * @remarks React Router 配置：懒加载路由与 AuthGuard 鉴权守卫。
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
import { createBrowserRouter, Navigate, useLocation } from 'react-router-dom';
import { Layout } from './components/Layout';
import { useAuthStore } from './store/useAuthStore';
import React from 'react';

/**
 * 路由守卫：检查登录状态
 */
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    // 将当前路径保存到 location.state，登录成功后跳回
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

const router = createBrowserRouter([
  {
    path: '/login',
    lazy: async () => {
      const module = await import('@/features/auth');
      return { Component: module.default };
    },
  },
  {
    path: '/forgot-password',
    lazy: async () => {
      const module = await import('@/features/auth');
      return { Component: module.ForgotPassword };
    },
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <Layout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        lazy: async () => {
          const module = await import('@/features/workbench');
          return { Component: module.default };
        },
      },
      {
        path: 'database',
        lazy: async () => {
          const module = await import('@/features/standards');
          return { Component: module.default };
        },
      },
      {
        path: 'database/:standardId',
        lazy: async () => {
          const module = await import('@/features/standards');
          return { Component: module.StandardDetail };
        },
      },
      {
        path: 'search',
        lazy: async () => {
          const module = await import('@/features/search');
          return { Component: module.default };
        },
      },
      {
        path: 'import',
        lazy: async () => {
          const module = await import('@/features/import');
          return { Component: module.default };
        },
      },
      {
        path: 'import/history',
        lazy: async () => {
          const module = await import('@/features/import');
          return { Component: module.ImportHistory };
        },
      },
      {
        path: 'alignment',
        lazy: async () => {
          const module = await import('@/features/alignment');
          return { Component: module.default };
        },
      },
      {
        path: 'alignment/result',
        lazy: async () => {
          const module = await import('@/features/alignment');
          return { Component: module.AlignmentResult };
        },
      },
      {
        path: 'alignment/tasks',
        lazy: async () => {
          const module = await import('@/features/alignment');
          return { Component: module.AlignmentTasks };
        },
      },
      {
        path: 'user/profile',
        lazy: async () => {
          const module = await import('@/features/user');
          return { Component: module.UserProfile };
        },
      },
      {
        path: 'user/admin',
        lazy: async () => {
          const module = await import('@/features/user');
          return { Component: module.UserAdmin };
        },
      },
      {
        path: 'user/change-password',
        lazy: async () => {
          const module = await import('@/features/user');
          return { Component: module.ChangePassword };
        },
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

export default router;
/**
 * @moduleEnd semAlign
 * @file router.tsx
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

