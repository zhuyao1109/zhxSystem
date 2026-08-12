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
