import { create } from 'zustand';
import type { User } from '@/types';

interface AuthState {
  token: string | null;
  tokenExpiresAt: number | null;
  user: User | null;
  isAuthenticated: boolean;

  setAuth: (token: string, user: User, expiresIn?: number) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  token: null,
  tokenExpiresAt: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token, user, expiresIn = 30 * 60 * 1000) => {
    const expiresAt = Date.now() + expiresIn;
    set({ token, user, isAuthenticated: true, tokenExpiresAt: expiresAt });
    // 仅保存 token 供当前浏览器会话内请求使用；不再持久化 Zustand 自动登录状态。
    localStorage.setItem('token', token);
    localStorage.setItem('token_expires_at', expiresAt.toString());
    localStorage.removeItem('auth-storage');
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('token_expires_at');
    localStorage.removeItem('auth-storage');
    set({ token: null, user: null, isAuthenticated: false, tokenExpiresAt: null });
  },
  updateUser: (updatedUser) => set((state) => ({
    user: state.user ? { ...state.user, ...updatedUser } : null
  })),
}));
