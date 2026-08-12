import React from 'react';
import type { StatusType } from '@/types';
import { STATUS_CONFIG } from '@/constants';

export interface BadgeProps {
  status: StatusType | string;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ status, className = '' }) => {
  const config = STATUS_CONFIG[status as StatusType] || {
    label: status,
    color: 'bg-gray-400',
    textColor: 'text-gray-600',
  };

  return (
    <span
      className={`inline-flex items-center justify-center min-w-16 px-2.5 py-1 rounded-full text-xs font-medium ${config.color} text-white ${className}`}
    >
      <span className="whitespace-nowrap">{config.label}</span>
    </span>
  );
};

export default Badge;
