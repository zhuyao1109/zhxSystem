import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui';
import type { Dynamic } from '@/types';

export interface DynamicListProps {
  dynamics: Dynamic[];
}

export const DynamicList: React.FC<DynamicListProps> = ({ dynamics }) => {
  const navigate = useNavigate();

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
