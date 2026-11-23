// frontend/src/pages/OverviewPage.tsx
// High-level dashboard showing system health, core principle, recent datasets, and workflow triggers.

import React from 'react';
import {
  UploadCloud,
  FileCheck2,
  Sparkles,
  ShieldCheck,
  Cpu,
  Database,
  BarChart3,
  Terminal,
} from 'lucide-react';
import type { HealthStatus, DatasetModel, AnalysisModel, PageId } from '../types';

interface OverviewPageProps {
  onNavigate: (page: PageId) => void;
  health: HealthStatus | null;
  datasets: DatasetModel[];
  analyses: AnalysisModel[];
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  onNavigate,
  health,
  datasets,
  analyses,
}) => {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl glass-panel p-6 sm:p-8 border border-navy-750 bg-gradient-to-br from-navy-900 via-navy-850 to-navy-950">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-cyan/10 border border-brand-cyan/20 text-brand-cyan text-xs font-semibold mb-4">
            <ShieldCheck className="w-4 h-4" />
            <span>Deterministic Analytics Core</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Grounded Business Intelligence.
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-cyan via-blue-400 to-indigo-400">
              Where AI Never Invents Numbers.
            </span>
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed">
            Upload messy business spreadsheets, JSON, or PDFs. InsightForge profiles schemas, runs
            reproducible Python (Pandas) calculations, and translates results into auditable,
            evidence-linked insights with zero mathematical hallucinations.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('upload')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-600/30 transition transform hover:-translate-y-0.5"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Business Files</span>
            </button>
            <button
              onClick={() => onNavigate('explorer')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-navy-800 hover:bg-navy-700 text-slate-200 text-sm font-semibold border border-navy-700 transition"
            >
              <Database className="w-4 h-4" />
              <span>Explore Data & Schemas</span>
            </button>
          </div>
        </div>

        {/* Ambient background decoration */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Core Principle Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card rounded-2xl p-5 border border-navy-750">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
            <Terminal className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">Deterministic Engine</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Every metric (revenue, margins, period growth, anomaly scores) is strictly calculated
            by pandas algorithms. No generated code executes blindly.
          </p>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-navy-750">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-4">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">Grounded AI Explanations</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            The AI Analyst explains results in plain English, citing exact formulas and data sources.
            If data is missing, it honestly states what is missing instead of guessing.
          </p>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-navy-750">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
            <FileCheck2 className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">Auditable Evidence Chain</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Every insight card is an immutable object containing original row references, formula
            definitions, and separate confidence ratings for college review.
          </p>
        </div>
      </div>

      {/* System Status & Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-4 border border-navy-750">
          <div className="text-xs text-slate-400 uppercase font-mono">Backend Service</div>
          <div className="mt-1 flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                health?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="text-lg font-bold text-white">
              {health ? health.service : 'Connecting...'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            FastAPI v{health?.version || '1.0'} on 127.0.0.1:8000
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-navy-750">
          <div className="text-xs text-slate-400 uppercase font-mono">AI Provider State</div>
          <div className="mt-1 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-cyan" />
            <span className="text-lg font-bold text-white">
              {health?.ai_configured ? health.provider.toUpperCase() : 'Deterministic Local'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            {health?.ai_configured ? `Active Model: ${health.model}` : '100% Offline Math Fallback'}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-navy-750">
          <div className="text-xs text-slate-400 uppercase font-mono">Active Datasets</div>
          <div className="mt-1 text-2xl font-extrabold text-white font-mono">
            {datasets.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Uploaded in local SQLite store</div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-navy-750">
          <div className="text-xs text-slate-400 uppercase font-mono">Analyses Completed</div>
          <div className="mt-1 text-2xl font-extrabold text-white font-mono">
            {analyses.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Ready for dashboard & PDF export</div>
        </div>
      </div>

      {/* Quick Jump Pipeline Overview */}
      <div className="glass-panel rounded-2xl p-6 border border-navy-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-brand-cyan" />
            InsightForge 8-Step Analytical Pipeline
          </h2>
          <span className="text-xs font-mono text-slate-400">PRD Section 10</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          {[
            { step: '1. Upload', desc: 'MIME, size & safe parsing (no macros)' },
            { step: '2. Profile', desc: 'Detect column types & missing values' },
            { step: '3. Suggest', desc: 'Infers revenue, dates, customer IDs' },
            { step: '4. Confirm', desc: 'User verifies schema before compute' },
            { step: '5. Clean', desc: 'Original data kept untouched + audit log' },
            { step: '6. Compute', desc: 'Pure pandas stats, trends, margins' },
            { step: '7. Build Insights', desc: 'Fact + Interpretation + Action split' },
            { step: '8. Validate', desc: 'Numbers re-checked before UI presentation' },
          ].map((item, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-navy-900/80 border border-navy-800/80 hover:border-navy-700 transition"
            >
              <div className="font-semibold text-slate-200">{item.step}</div>
              <div className="text-slate-400 text-[11px] mt-0.5">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
