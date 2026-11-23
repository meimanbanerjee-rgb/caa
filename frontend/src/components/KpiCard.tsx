// frontend/src/components/KpiCard.tsx
// Glassmorphic KPI card with title, verified value, formula label, and trend indicators.

import React from 'react';
import { CheckCircle2, TrendingUp, TrendingDown } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: string;
  isPositive?: boolean;
  formula?: string;
  source?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  change,
  isPositive,
  formula,
  source,
}) => {
  return (
    <div className="glass-card rounded-2xl p-5 border border-navy-750 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <span className="font-medium tracking-wide uppercase">{title}</span>
          <span
            className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono"
            title="Computed deterministically by Python Pandas"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Verified
          </span>
        </div>

        <div className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight font-mono">
          {value}
        </div>

        {change && (
          <div
            className={`mt-2 flex items-center gap-1 text-xs font-semibold ${
              isPositive ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            <span>{change}</span>
            {subtitle && <span className="text-slate-400 font-normal ml-1">vs {subtitle}</span>}
          </div>
        )}
      </div>

      {(formula || source) && (
        <div className="mt-4 pt-3 border-t border-navy-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          {formula && (
            <span className="truncate max-w-[200px]" title={formula}>
              fx: {formula}
            </span>
          )}
          {source && <span className="text-slate-500 truncate">{source}</span>}
        </div>
      )}
    </div>
  );
};
