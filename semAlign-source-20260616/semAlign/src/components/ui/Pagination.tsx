import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface PaginationProps {
  current: number;
  pageSize: number;
  total: number;
  onChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
}

export const Pagination: React.FC<PaginationProps> = ({
  current,
  pageSize,
  total,
  onChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
}) => {
  const totalPages = Math.ceil(total / pageSize);
  const hasPrev = current > 1;
  const hasNext = current < totalPages;

  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    if (current <= 4) {
      return [1, 2, 3, 4, 5, '...', totalPages];
    } else if (current >= totalPages - 3) {
      return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
    } else {
      return [1, '...', current - 1, current, current + 1, '...', totalPages];
    }
  };

  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-slate-600">
        共 <span className="font-medium">{total}</span> 条，第{' '}
        <span className="font-medium">{current}</span> / {totalPages} 页
      </div>

      <div className="flex items-center gap-2">
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
          className="px-2 py-1 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size}条/页
            </option>
          ))}
        </select>

        <button
          onClick={() => onChange?.(current - 1)}
          disabled={!hasPrev}
          className="p-2 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {getPageNumbers().map((page) => (
          <React.Fragment key={typeof page === 'number' ? `page-${page}` : 'page-ellipsis'}>
            {page === '...' ? (
              <span className="px-3 py-2 text-slate-400">...</span>
            ) : (
              <button
                onClick={() => onChange?.(page)}
                className="px-3 py-2 rounded border"
                style={{
                  backgroundColor: current === page ? '#2563eb' : 'transparent',
                  color: current === page ? '#ffffff' : '#475569',
                  borderColor: current === page ? '#2563eb' : '#cbd5e1',
                }}
              >
                {page}
              </button>
            )}
          </React.Fragment>
        ))}

        <button
          onClick={() => onChange?.(current + 1)}
          disabled={!hasNext}
          className="p-2 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default Pagination;