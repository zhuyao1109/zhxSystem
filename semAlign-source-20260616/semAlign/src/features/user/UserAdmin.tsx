import React, { useEffect, useState } from 'react';
import { Shield, Users } from 'lucide-react';
import { Card } from '@/components/ui';
import userApi, { type UserProfile } from '@/api/modules/user';
import { getApiErrorMessage } from '@/utils/apiError';
import { useToast } from '@/components/common';

const UserAdmin: React.FC = () => {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { showSuccess, showError } = useToast();

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
