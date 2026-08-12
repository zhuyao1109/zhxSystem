import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export const Loading: React.FC<LoadingProps> = ({
  size = 'md',
  text,
  className = '',
}) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loader2 className={`${sizes[size]} animate-spin text-blue-600`} />
      {text && <span className="text-slate-500 text-sm">{text}</span>}
    </div>
  );
};

export const PageLoading: React.FC = () => (
  <div className="flex items-center justify-center min-h-[400px]">
    <Loading size="lg" text="加载中..." />
  </div>
);

export interface SkeletonProps {
  lines?: number;
  avatar?: boolean;
  className?: string;
}

const SKELETON_LINE_IDS = ['sk-a', 'sk-b', 'sk-c', 'sk-d', 'sk-e', 'sk-f', 'sk-g', 'sk-h'] as const;

export const Skeleton: React.FC<SkeletonProps> = ({
  lines = 3,
  avatar = false,
  className = '',
}) => (
  <div className={`animate-pulse space-y-4 ${className}`}>
    {avatar && (
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 bg-slate-200 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-slate-200 rounded w-1/3" />
          <div className="h-3 bg-slate-200 rounded w-1/4" />
        </div>
      </div>
    )}
    {SKELETON_LINE_IDS.slice(0, lines).map((lineId, i) => (
      <div
        key={lineId}
        className="h-4 bg-slate-200 rounded"
        style={{ width: `${70 + (i % 3) * 10}%` }}
      />
    ))}
  </div>
);

export default Loading;
