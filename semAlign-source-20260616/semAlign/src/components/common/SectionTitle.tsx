import React from 'react';

export interface SectionTitleProps {
  title: string;
  subtitle?: string;
}

export const SectionTitle: React.FC<SectionTitleProps> = ({ title, subtitle }) => (
  <div className="mb-6">
    <div className="flex items-center gap-3 mb-1">
      <div className="w-1 h-6 bg-blue-600 rounded-sm" />
      <h2 className="text-xl font-bold text-slate-800">{title}</h2>
    </div>
    {subtitle && <p className="text-sm text-slate-500 ml-4">{subtitle}</p>}
  </div>
);

export default SectionTitle;
