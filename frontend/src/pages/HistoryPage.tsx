// frontend/src/pages/HistoryPage.tsx
// History page for reviewing past analysis sessions and audit trails.

import React from 'react';
import {
  History,
  Calendar,
  BarChart3,
  FileSpreadsheet,
} from 'lucide-react';
import type { AnalysisModel, PageId } from '../types';

interface HistoryPageProps {
  analyses: AnalysisModel[];
  onSelectAnalysis: (analysis: AnalysisModel) => void;
  onNavigate: (page: PageId) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  analyses,
  onSelectAnalysis,
  onNavigate,
}) => {
  return (
    <div className="space-y-6 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div className="pb-4 border-b border-navy-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase text-brand-cyan tracking-wider font-semibold">
            Audit Archive
          </span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-400">
            Persistent SQLite Store
          </span>
        </div>
        <h1 className="text-2xl font-extrabold text-white mt-1">Analysis History</h1>
        <p className="text-xs text-slate-300">
          Revisit previous analysis sessions, check mathematical evidence trails, or export archived reports.
        </p>
      </div>

      {/* History List */}
      {analyses.length === 0 ? (
        <div className="p-12 text-center rounded-3xl glass-panel max-w-md mx-auto my-8 border border-navy-800">
          <History className="w-12 h-12 text-slate-500 mx-auto mb-3" />
          <h2 className="text-base font-bold text-white">No Analysis History Found</h2>
          <p className="mt-1 text-xs text-slate-400">
            Once you execute an analytics run on a dataset, its verified record is saved here.
          </p>
          <button
            onClick={() => onNavigate('upload')}
            className="mt-4 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition"
          >
            Start First Analysis
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {analyses.map((analysis) => (
            <div
              key={analysis.id}
              className="glass-card rounded-2xl p-5 border border-navy-800 flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{analysis.id}</span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-brand-cyan border border-blue-500/20 uppercase">
                    {analysis.domain}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(analysis.created_at).toLocaleString()}
                  </span>
                  <span>•</span>
                  <span>{analysis.metrics.row_count || 0} rows processed</span>
                  <span>•</span>
                  <span>{analysis.insights.length} verified insights</span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  onClick={() => {
                    onSelectAnalysis(analysis);
                    onNavigate('insights');
                  }}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition"
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>Open Dashboard</span>
                </button>

                <button
                  onClick={() => {
                    onSelectAnalysis(analysis);
                    onNavigate('reports');
                  }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-navy-850 hover:bg-navy-800 text-slate-300 text-xs font-semibold border border-navy-750 transition"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-brand-cyan" />
                  <span>Report</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
