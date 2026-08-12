import { useEffect } from 'react';
import { useAuthStore } from '@/store/useAuthStore';

/**
 * 认证状态管理 Hook
 * 
 * 功能：
 * - 自动检查 token 是否过期
 * - 过期时自动清除认证信息
 */
export function useAuth() {
  const { token, tokenExpiresAt, logout } = useAuthStore();

  useEffect(() => {
    // 检查 token 是否过期
    if (tokenExpiresAt && Date.now() > tokenExpiresAt) {
      console.warn('Token 已过期，自动登出');
      logout();
      
      // 如果当前不在登录页，跳转到登录页
      const currentPath = window.location.pathname;
      if (currentPath !== '/login') {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
      }
    }
  }, [tokenExpiresAt, logout]);

  // 检查 token 是否即将过期（剩余时间少于 5 分钟）
  const isTokenExpiringSoon = tokenExpiresAt 
    ? (tokenExpiresAt - Date.now()) < 5 * 60 * 1000 
    : false;

  return {
    token,
    tokenExpiresAt,
    isTokenExpiringSoon,
    logout,
  };
}