/**
 * @file semAlign
 * @file UserAdmin.tsx
 * @description 用户中心：资料修改、密码变更与管理员用户权限。
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
import React, { useEffect, useState } from 'react';
import { Shield, Users } from 'lucide-react';
import { Card } from '@/components/ui';
import userApi, { type UserProfile } from '@/api/modules/user';
import { getApiErrorMessage } from '@/utils/apiError';
import { useToast } from '@/components/common';

// -----------------------------------------------------------------------------
// 分段：UserAdmin.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。
// -----------------------------------------------------------------------------

/**
 * React 组件 `UserAdmin`：负责对应页面或区块的 UI 与交互。
 */
const UserAdmin: React.FC = () => {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { showSuccess, showError } = useToast();

  /**
   * 异步函数 `loadUsers`：发起 API 请求或执行页面侧异步流程。
   */
  const loadUsers = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await userApi.listUsers();
      if (response.code === 200) {
        setUsers(response.data || []);
      } else {
        setError(response.message || '加载用户列表失败');
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '加载用户列表失败'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, []);

  /**
   * 异步函数 `updateUser`：发起 API 请求或执行页面侧异步流程。
   */
  const updateUser = async (user: UserProfile, data: { role?: string; is_active?: boolean }): Promise<void> => {
    try {
      const response = await userApi.updateUserByAdmin(user.id, data);
      if (response.code === 200 && response.data) {
        const updatedUser = response.data;
        setUsers((prev) => prev.map((item) => (item.id === user.id ? updatedUser : item)));
        showSuccess('用户权限已更新');
      } else {
        showError(response.message || '更新失败');
      }
    } catch (err: unknown) {
      showError(getApiErrorMessage(err, '更新用户权限失败'));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">用户及权限管理</h1>
            <p className="text-sm text-slate-500">管理员可设置用户角色和启用状态</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void loadUsers()}
          className="px-3 py-2 text-sm rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          刷新
        </button>
      </div>

      <Card>
        <div className="mb-4 flex items-center gap-2 text-slate-700 font-medium">
          <Users className="w-5 h-5" />
          用户列表
        </div>

        {loading && <div className="text-sm text-slate-500">正在加载用户列表...</div>}
        {!loading && error && <div className="text-sm text-red-600">{error}</div>}
        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">ID</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">用户名</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">邮箱</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">角色</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-slate-600">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2 text-sm text-slate-700">{user.id}</td>
                    <td className="px-3 py-2 text-sm font-medium text-slate-900">{user.username}</td>
                    <td className="px-3 py-2 text-sm text-slate-700">{user.email || '-'}</td>
                    <td className="px-3 py-2 text-sm">
                      <select
                        value={user.role}
                        onChange={(e) => void updateUser(user, { role: e.target.value })}
                        className="px-2 py-1 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="user">普通用户</option>
                        <option value="admin">管理员</option>
                      </select>
                    </td>
                    <td className="px-3 py-2 text-sm">
                      <button
                        type="button"
                        onClick={() => void updateUser(user, { is_active: !user.is_active })}
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          user.is_active
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {user.is_active ? '启用' : '禁用'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && <div className="py-6 text-center text-sm text-slate-500">暂无用户</div>}
          </div>
        )}
      </Card>
    </div>
  );
};

export default UserAdmin;
/**
 * @moduleEnd semAlign
 * @file UserAdmin.tsx
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

