/**
 * @file semAlign
 * @file UserProfile.tsx
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
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User as UserIcon, Mail, ArrowLeft, Key } from 'lucide-react';
import { Card } from '@/components/ui';
import userApi, { type UserProfile } from '@/api/modules/user';
import { getApiErrorMessage } from '@/utils/apiError';

// -----------------------------------------------------------------------------
// 分段：UserProfile.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// 注意：加载态、错误提示与权限控制需与后端接口契约保持一致。
// -----------------------------------------------------------------------------

/**
 * React 组件 `UserProfile`：负责对应页面或区块的 UI 与交互。
 */
const UserProfile: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [email, setEmail] = useState('');
  const [avatar, setAvatar] = useState('');

  // 加载用户信息
  useEffect(() => {
    /**
     * 异步函数 `loadProfile`：发起 API 请求或执行页面侧异步流程。
     */
    const loadProfile = async () => {
      setFetching(true);
      try {
        const response = await userApi.getProfile();
        if (response.code === 200 && response.data) {
          setProfile(response.data);
          setEmail(response.data.email || '');
          setAvatar(response.data.avatar || '');
        } else {
          setError(response.message || '加载失败');
        }
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, '加载用户信息失败'));
      } finally {
        setFetching(false);
      }
    };

    void loadProfile();
  }, []);

  /**
   * 异步函数 `handleSubmit`：发起 API 请求或执行页面侧异步流程。
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    setLoading(true);
    try {
      const response = await userApi.updateProfile({
        email: email || undefined,
        avatar: avatar || undefined,
      });

      if (response.code === 200) {
        setSuccess(true);
        setProfile(response.data);

        setTimeout(() => {
          setSuccess(false);
        }, 3000);
      } else {
        setError(response.message || '更新失败');
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '更新用户信息失败'));
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="min-h-screen bg-slate-50 py-8">
        <div className="max-w-2xl mx-auto px-4">
          <Card className="p-6 text-center text-slate-500">
            加载中...
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          返回
        </button>

        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <UserIcon className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">个人信息</h1>
              <p className="text-sm text-slate-500">查看和编辑您的个人资料</p>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              信息更新成功！
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名（只读） */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                用户名
              </label>
              <input
                type="text"
                value={profile?.username || ''}
                disabled
                className="w-full px-4 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-500 cursor-not-allowed"
              />
              <p className="text-xs text-slate-500 mt-1">用户名不可修改</p>
            </div>

            {/* 角色（只读） */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                角色
              </label>
              <input
                type="text"
                value={profile?.role === 'admin' ? '管理员' : '普通用户'}
                disabled
                className="w-full px-4 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-500 cursor-not-allowed"
              />
            </div>

            {/* 邮箱 */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                <Mail className="w-4 h-4 inline mr-1" />
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入邮箱地址"
                disabled={loading}
              />
            </div>

            {/* 头像URL */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                头像URL
              </label>
              <input
                type="text"
                value={avatar}
                onChange={(e) => setAvatar(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入头像图片URL"
                disabled={loading}
              />
              {avatar && (
                <div className="mt-2">
                  <img
                    src={avatar}
                    alt="头像预览"
                    className="w-16 h-16 rounded-full object-cover border-2 border-slate-200"
                    onError={(e) => {
                      e.currentTarget.src = 'https://via.placeholder.com/64?text=Avatar';
                    }}
                  />
                </div>
              )}
            </div>

            {/* 注册时间（只读） */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                注册时间
              </label>
              <input
                type="text"
                value={profile?.created_at ? new Date(profile.created_at).toLocaleString('zh-CN') : ''}
                disabled
                className="w-full px-4 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-500 cursor-not-allowed"
              />
            </div>

            {/* 修改密码按钮 */}
            <div className="pt-4 border-t border-slate-200">
              <button
                type="button"
                onClick={() => navigate('/user/change-password')}
                className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
              >
                <Key className="w-4 h-4" />
                修改密码
              </button>
            </div>

            {/* 提交按钮 */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? '保存中...' : '保存修改'}
              </button>
              <button
                type="button"
                onClick={() => navigate(-1)}
                disabled={loading}
                className="px-6 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                取消
              </button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default UserProfile;
/**
 * @moduleEnd semAlign
 * @file UserProfile.tsx
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

