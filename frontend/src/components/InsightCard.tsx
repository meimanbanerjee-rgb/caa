// frontend/src/components/InsightCard.tsx
// Structured Insight card separating Fact, Interpretation, and Recommendation (PRD G2, FR-16).

import React from 'react';
import {
  FileSearch,
  Lightbulb,
  Compass,
  CheckCircle,
} from 'lucide-react';
import type { InsightModel } from '../types';

interface InsightCardProps {
  insight: InsightModel;
  onViewEvidence: (insight: InsightModel) => void;
}

export const InsightCard: React.FC<InsightCardProps> = ({ insight, onViewEvidence }) => {
  const priorityStyles: Record<string, string> = {
    critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    high: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    medium: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    low: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  };

  return (
    <div className="glass-card rounded-2xl p-6 border border-navy-750 flex flex-col justify-between">
      <div>
        {/* Top badges */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border uppercase tracking-wider ${
                priorityStyles[insight.priority] || priorityStyles.medium
              }`}
            >
              {insight.priority} Priority
            </span>
            <span className="text-xs text-slate-400 font-medium capitalize bg-navy-850 px-2 py-0.5 rounded border border-navy-700">
              {insight.category}
            </span>
          </div>

          <button
            onClick={() => onViewEvidence(insight)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-medium text-brand-cyan hover:bg-brand-cyan/10 border border-brand-cyan/30 transition"
            title="Inspect calculation formula, row sources, and evidence cache"
          >
            <FileSearch className="w-3.5 h-3.5" />
            Audit Evidence
          </button>
        </div>

        {/* Title & Plain English Summary */}
        <h3 className="text-base font-bold text-white mb-2">{insight.title}</h3>
        <p className="text-xs text-slate-300 leading-relaxed mb-4">
          {insight.plain_english_explanation}
        </p>

        {/* STRICT TRIPLE SEPARATION (PRD G2) */}
        <div className="space-y-2.5 text-xs">
          {/* 1. Fact (Pure Math) */}
          <div className="p-3 rounded-xl bg-navy-900/90 border border-emerald-500/20">
            <div className="flex items-center gap-1.5 text-emerald-400 font-semibold mb-1">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Calculated Fact (Deterministic)</span>
            </div>
            <p className="text-slate-200">{insight.observed_fact}</p>
          </div>

          {/* 2. Interpretation (Business Reason) */}
          <div className="p-3 rounded-xl bg-navy-900/90 border border-blue-500/20">
            <div className="flex items-center gap-1.5 text-blue-400 font-semibold mb-1">
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Interpretation (Plausible Reason)</span>
            </div>
            <p className="text-slate-300">{insight.interpretation}</p>
          </div>

          {/* 3. Recommendation (Action) */}
          <div className="p-3 rounded-xl bg-navy-900/90 border border-brand-cyan/20">
            <div className="flex items-center gap-1.5 text-brand-cyan font-semibold mb-1">
              <Compass className="w-3.5 h-3.5" />
              <span>Recommendation (Suggested Next Step)</span>
            </div>
            <p className="text-slate-300">{insight.recommendation}</p>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-3 border-t border-navy-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <span className="truncate max-w-[220px]">
          Source: {insight.source.filename} ({insight.source.sheet || 'Table'})
        </span>
        <span className="font-mono text-slate-500">{insight.reliability.statistical_confidence}</span>
      </div>
    </div>
  );
};
