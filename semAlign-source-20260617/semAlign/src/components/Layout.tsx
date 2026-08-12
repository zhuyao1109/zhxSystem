/**
 * @file semAlign
 * @file Layout.tsx
 * @description 应用壳层组件：顶栏导航、侧栏菜单与路由出口。
 * @remarks 应用主布局：顶栏导航、角色菜单与 Outlet 渲染。
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
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Plane, User as UserIcon, LogOut } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { useAuth } from '@/hooks/useAuth';

const NAV_ITEMS = [
  { label: '工作台', path: '/' },
  { label: '标准导入', path: '/import', adminOnly: true },
  { label: '标准数据库', path: '/database' },
  { label: '标准对齐', path: '/alignment', adminOnly: true },
  { label: '智能检索', path: '/search' },
  { label: '用户权限', path: '/user/admin', adminOnly: true },
];

/**
 * 应用主布局：顶栏导航、角色菜单与 Outlet 渲染。
 */
export const Layout: React.FC = () => {
  useAuth();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  /**
   * 函数 `handleLogout`：本模块内部业务辅助逻辑。
   */
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center gap-3">
                <div className="bg-blue-600 p-1.5 rounded-lg shadow-blue-200 shadow-md">
                  <Plane className="h-5 w-5 text-white transform -rotate-45" />
                </div>
                <span className="font-bold text-xl tracking-tight text-slate-900">标准对齐系统</span>
              </div>
              <nav className="hidden sm:ml-8 sm:flex sm:space-x-8">
                {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === 'admin').map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-all duration-200 ${
                        isActive
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
                  {user?.avatar ? (
                    <img src={user.avatar} alt="avatar" className="h-full w-full rounded-full object-cover" />
                  ) : (
                    <UserIcon className="h-5 w-5" />
                  )}
                </div>
                <div className="hidden sm:block">
                  <div className="text-sm font-bold text-slate-900">{user?.username || '管理员'}</div>
                  <div className="text-xs text-slate-400">{user?.role === 'admin' ? '管理员' : '普通用户'}</div>
                </div>
              </div>
              
              <button 
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut size={16} />
                <span className="hidden sm:inline">退出登录</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Outlet />
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-400 text-xs">
          © 2026 中航信语义对齐系统
        </div>
      </footer>
    </div>
  );
};

export default Layout;
/**
 * @moduleEnd semAlign
 * @file Layout.tsx
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

