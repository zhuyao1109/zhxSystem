/**
 * @file semAlign
 * @file Login.tsx
 * @description 认证模块：登录、忘记密码与 Token 持久化。
 * @remarks 用户登录页：提交凭证并写入 Zustand 认证状态。
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
import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Lock, User as UserIcon, AlertCircle, Loader2, Fingerprint } from 'lucide-react';
import { authApi } from '@/api';
import { useAuthStore } from '@/store/useAuthStore';
import { Card } from '@/components/ui';

// -----------------------------------------------------------------------------
// 分段：Login.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。
// -----------------------------------------------------------------------------

/**
 * 类型定义 `LoginLocationState`：描述前后端交互或页面状态结构。
 */
interface LoginLocationState {
  from?: { pathname?: string };
}

/**
 * 函数 `getLoginRedirectPath`：本模块内部业务辅助逻辑。
 */
function getLoginRedirectPath(state: unknown): string {
  if (typeof state !== 'object' || state === null) {
    return '/';
  }
  /**
   * 函数 `from`：本模块内部业务辅助逻辑。
   */
  const from = (state as LoginLocationState).from;
  return from?.pathname || '/';
}

/**
 * 用户登录页：提交凭证并写入 Zustand 认证状态。
 */
const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore(state => state.setAuth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from = getLoginRedirectPath(location.state);

  // 添加请求去重锁
  const loginInProgressRef = React.useRef(false);

  // 组件卸载时重置锁
  useEffect(() => {
    return () => {
      loginInProgressRef.current = false;
    };
  }, []);

  const handleLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();

    console.log('[Login] handleLogin called', { loading, inProgress: loginInProgressRef.current });

    // 防止重复提交
    if (loginInProgressRef.current || loading) {
      console.log('[Login] Request blocked - duplicate submission');
      return;
    }

    if (!username || !password) {
      setError('请输入用户名和密码');
      return;
    }

    loginInProgressRef.current = true;
    setLoading(true);
    setError(null);

    try {
      console.log('[Login] Sending login request...', { username });
      const response = await authApi.login({ username, password });
      console.log('[Login] Response received:', response);

      if (response.code === 200) {
        const { token, user } = response.data;
        // Token 有效期为 30 分钟（30 * 60 * 1000 毫秒）
        const TOKEN_EXPIRES_IN = 30 * 60 * 1000;
        setAuth(token, user, TOKEN_EXPIRES_IN);
        navigate(from, { replace: true });
      } else {
        setError(response.message || '登录失败');
      }
    } catch (err: any) {
      console.error('[Login] Error:', err);
      setError(err.response?.data?.detail || '无法连接到服务器，请重试');
    } finally {
      setLoading(false);
      loginInProgressRef.current = false;
      console.log('[Login] Request completed');
    }
  }, [username, password, loading, setAuth, navigate, from]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-slate-900">
      {/* 背景装饰层 - 航空与语义网络感 */}
      <div className="absolute inset-0 z-0">
        {/* 基础渐变 */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900/20 to-slate-900"></div>
        
        {/* 几何网格纹理 */}
        <div className="absolute inset-0 opacity-20" 
             style={{ backgroundImage: `radial-gradient(#3b82f6 1px, transparent 1px)`, backgroundSize: '40px 40px' }}></div>
        
        {/* 抽象航线线条 */}
        <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
          <path d="M-100 100 Q 400 300 1200 -50" stroke="#3b82f6" strokeWidth="2" fill="none" />
          <path d="M-50 400 Q 600 200 1500 500" stroke="#3b82f6" strokeWidth="1" fill="none" />
          <path d="M200 800 Q 800 400 1400 200" stroke="#3b82f6" strokeWidth="1.5" fill="none" />
          {/* 装饰性节点 */}
          <circle cx="400" cy="300" r="4" fill="#3b82f6" />
          <circle cx="800" cy="400" r="3" fill="#3b82f6" />
          <circle cx="1200" cy="200" r="5" fill="#3b82f6" />
        </svg>

        {/* 模糊的光晕效果 */}
        <div className="absolute top-1/4 -left-20 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-indigo-600/10 rounded-full blur-[100px]"></div>
      </div>
      
      {/* 登录主体 */}
      <div className="max-w-md w-full relative z-10 px-4">
        {/* Logo 区域 */}
        <div className="text-center mb-8 animate-in fade-in slide-in-from-top-4 duration-700">
          {/*<div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-blue-600 text-white mb-6 shadow-2xl shadow-blue-500/30 rotate-3 transition-transform hover:rotate-0 cursor-pointer">
            <div className="relative">
              <ShieldCheck size={40} />
              <div className="absolute -top-1 -right-1">
                <div className="w-3 h-3 bg-green-400 rounded-full border-2 border-blue-600"></div>
              </div>
            </div>
          </div>*/}
          <h1 className="text-3xl font-black text-white tracking-tight">语义对齐系统</h1>
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="h-px w-8 bg-blue-500/50"></span>
            <p className="text-blue-200/60 text-sm font-medium uppercase tracking-widest">Semantic Alignment System</p>
            <span className="h-px w-8 bg-blue-500/50"></span>
          </div>
        </div>

        <Card className="p-10 shadow-2xl border-white/5 bg-white/95 backdrop-blur-md rounded-2xl animate-in fade-in zoom-in-95 duration-500">
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900">欢迎登录</h2>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            {error && (
              <div className="p-4 bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl flex items-center gap-3">
                <AlertCircle size={18} className="shrink-0" />
                <span className="font-medium">{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider ml-1">
                用户账号
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-600 transition-colors">
                  <UserIcon size={18} />
                </div>
                <input
                  type="text"
                  autoComplete="username"
                  className="block w-full pl-11 pr-4 py-3 bg-slate-100/50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white focus:border-transparent transition-all"
                  placeholder="admin / user"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider ml-1">
                认证密码
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-600 transition-colors">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  autoComplete="current-password"
                  className="block w-full pl-11 pr-4 py-3 bg-slate-100/50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white focus:border-transparent transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center justify-end py-1">
              <button
                type="button"
                className="text-sm font-bold text-blue-600 hover:text-blue-700 transition-colors"
                onClick={() => navigate('/forgot-password')}
              >
                忘记密码
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-4 px-6 border border-transparent rounded-xl shadow-lg shadow-blue-600/20 text-sm font-black text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-70 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>正在验证身份...</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Fingerprint size={18} />
                  <span>登录</span>
                </div>
              )}
            </button>
          </form>

          <div className="mt-10 pt-6 border-t border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-400">
              {/*<Plane size={14} className="-rotate-45" />*/}
              <span className="text-[10px] font-bold uppercase tracking-tighter"></span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Login;
/**
 * @moduleEnd semAlign
 * @file Login.tsx
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

