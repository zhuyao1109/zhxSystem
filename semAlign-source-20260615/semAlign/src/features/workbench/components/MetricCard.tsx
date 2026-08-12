import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { Card } from '@/components/ui';
import type { Metric } from '@/types';

export interface MetricCardProps {
  metric: Metric;
}

export const MetricCard: React.FC<MetricCardProps> = ({ metric }) => {
  const isPositive = metric.trend >= 0;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex flex-col h-full justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{metric.label}</p>
          <h3 className="text-4xl font-bold text-blue-600 mt-2 flex items-baseline gap-1">
            {metric.value}
            {metric.unit != null && metric.unit !== '' && (
              <span className="text-lg font-semibold text-slate-500">{metric.unit}</span>
            )}
          </h3>
        </div>
        <div className="flex items-center mt-4">
          {metric.trend !== 0 && (
            <span
              className={`flex items-center text-xs font-medium ${
                isPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
              {Math.abs(metric.trend)}%
            </span>
          )}
          {metric.trendLabel && (
            <span className="text-xs text-slate-400 ml-2">{metric.trendLabel}</span>
          )}
        </div>
      </div>
    </Card>
  );
};

export default MetricCard;
