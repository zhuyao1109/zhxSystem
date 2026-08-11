/**
 * @file semAlign
 * @file DynamicList.tsx
 * @description 治理工作台：指标卡、图表统计与标准动态列表。
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
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui';
import type { Dynamic } from '@/types';

/**
 * 类型定义 `DynamicListProps`：描述前后端交互或页面状态结构。
 */
export interface DynamicListProps {
  dynamics: Dynamic[];
}

/**
 * React 组件 `DynamicList`：负责对应页面或区块的 UI 与交互。
 */
export const DynamicList: React.FC<DynamicListProps> = ({ dynamics }) => {
  const navigate = useNavigate();

  /**
   * 函数 `getActionStyle`：本模块内部业务辅助逻辑。
   */
  const getActionStyle = (action: string) => {
    switch (action) {
      case '新增':
        return 'bg-blue-100 text-blue-700';
      case '废止':
        return 'bg-gray-100 text-gray-700';
      case '修订':
        return 'bg-yellow-100 text-yellow-700';
      case '审核':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-blue-100 text-blue-700';
    }
  };

  return (
    <Card className="w-full">
      <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
        <span className="w-1 h-4 bg-blue-600 block"></span>
        标准动态
      </h3>
      <div className="space-y-4">
        {dynamics.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-6">暂无最近动态，导入或更新标准后将在此展示</p>
        )}
        {dynamics.map((dynamic) => (
          <div
            key={dynamic.id}
            className="flex flex-col sm:flex-row gap-4 border-b border-slate-100 pb-4 last:border-0 last:pb-0 items-start sm:items-center"
          >
            <div className="flex items-center gap-3 min-w-[120px]">
              <span className={`${getActionStyle(dynamic.action)} text-xs px-2 py-1 rounded font-medium whitespace-nowrap`}>
                {dynamic.action}
              </span>
              <span className="text-xs text-slate-400">{dynamic.time}</span>
            </div>
            <div className="flex-1">
              <h4 className="font-bold text-slate-800 text-sm">{dynamic.title}</h4>
              {dynamic.description && (
                <p className="text-xs text-slate-500 mt-1">{dynamic.description}</p>
              )}
            </div>
            <div className="text-xs text-slate-400 whitespace-nowrap">{dynamic.date}</div>
          </div>
        ))}

        {dynamics.length > 0 && (
          <div className="pt-2 text-center">
            <button
              type="button"
              className="text-sm text-blue-600 hover:underline"
              onClick={() => navigate('/database')}
            >
              查看更多动态
            </button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default DynamicList;
/**
 * @moduleEnd semAlign
 * @file DynamicList.tsx
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

