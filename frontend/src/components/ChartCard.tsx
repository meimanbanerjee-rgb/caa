// frontend/src/components/ChartCard.tsx
// Interactive Recharts visualization card displaying real computed series.

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { BarChart3, TrendingUp, CheckCircle2 } from 'lucide-react';

interface ChartCardProps {
  title: string;
  type: 'bar' | 'line';
  data: any[];
  xKey: string;
  yKey: string;
  unit?: string;
}

const BAR_COLORS = ['#06b6d4', '#3b82f6', '#6366f1', '#10b981', '#f59e0b', '#ec4899'];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const val = payload[0].value;
    return (
      <div className="glass-panel p-3 rounded-xl border border-navy-700 bg-navy-950/95 text-xs shadow-xl">
        <p className="font-semibold text-white mb-1">{label}</p>
        <p className="text-brand-cyan font-mono font-bold">
          ${typeof val === 'number' ? val.toLocaleString(undefined, { minimumFractionDigits: 2 }) : val}
        </p>
      </div>
    );
  }
  return null;
};

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  type,
  data,
  xKey,
  yKey,
}) => {
  if (!data || data.length === 0) {
    return null;
  }

  return (
    <div className="glass-card rounded-2xl p-6 border border-navy-750 flex flex-col justify-between">
      {/* Chart Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {type === 'bar' ? (
            <BarChart3 className="w-5 h-5 text-brand-cyan" />
          ) : (
            <TrendingUp className="w-5 h-5 text-brand-cyan" />
          )}
          <h3 className="text-base font-bold text-white">{title}</h3>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-mono text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Real Results</span>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {type === 'bar' ? (
            <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1b2b48" vertical={false} />
              <XAxis
                dataKey={xKey}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#1b2b48' }}
              />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yKey} radius={[6, 6, 0, 0]}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1b2b48" vertical={false} />
              <XAxis
                dataKey={xKey}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#1b2b48' }}
              />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey={yKey}
                stroke="#06b6d4"
                strokeWidth={3}
                dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, fill: '#06b6d4' }}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Footer Info */}
      <div className="mt-3 pt-3 border-t border-navy-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span>Series: {yKey}</span>
        <span>Deterministic aggregation</span>
      </div>
    </div>
  );
};
