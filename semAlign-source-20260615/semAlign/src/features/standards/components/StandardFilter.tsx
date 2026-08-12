import React, { useState, useCallback } from 'react';
import { Search, Filter, Plus } from 'lucide-react';
import { Button } from '@/components/ui';
import { DEPARTMENTS, STATUS_CONFIG } from '@/constants';
import type { StandardsQueryParams } from '../standards.service';

export interface StandardFilterProps {
  onSearch?: (keyword: string) => void;
  onFilter?: (filters: Partial<StandardsQueryParams>) => void;
  onCreate?: () => void;
  loading?: boolean;
  statusOptions?: string[];
  departmentOptions?: string[];
}

export const StandardFilter: React.FC<StandardFilterProps> = ({
  onSearch,
  onFilter,
  onCreate,
  loading,
  statusOptions,
  departmentOptions,
}) => {
  const [keyword, setKeyword] = useState('');
  const statusItems = statusOptions && statusOptions.length > 0
    ? statusOptions
    : Object.values(STATUS_CONFIG).map((item) => item.label);
  const departmentItems = departmentOptions && departmentOptions.length > 0
    ? departmentOptions
    : DEPARTMENTS;

  const handleSearch = useCallback(() => {
    onSearch?.(keyword);
  }, [keyword, onSearch]);

  const handleFilterChange = useCallback(
    (key: keyof StandardsQueryParams, value: string) => {
      onFilter?.({ [key]: value || undefined });
    },
    [onFilter]
  );

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-white p-4 rounded-lg border border-slate-200">
      <div className="flex flex-1 gap-4 items-center w-full sm:w-auto">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="搜索标准编号或名称..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <select
          onChange={(e) => handleFilterChange('status', e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部状态</option>
          {statusItems.map((statusLabel) => (
            <option key={statusLabel} value={statusLabel}>
              {statusLabel}
            </option>
          ))}
        </select>

        <select
          onChange={(e) => handleFilterChange('department', e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部部门</option>
          {departmentItems.map((dept) => (
            <option key={dept} value={dept}>
              {dept}
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-3">
        <Button
          variant="secondary"
          icon={<Filter className="w-4 h-4" />}
          onClick={handleSearch}
          loading={loading}
        >
          搜索
        </Button>
        <Button icon={<Plus className="w-4 h-4" />} onClick={onCreate}>
          新增标准
        </Button>
      </div>
    </div>
  );
};

export default StandardFilter;
