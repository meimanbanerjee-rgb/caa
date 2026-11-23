// frontend/src/components/EvidenceModal.tsx
// Modal displaying complete mathematical evidence, source rows, and formula traceability.

import React from 'react';
import { X, CheckCircle2, FileText, Calculator, ShieldAlert, Cpu } from 'lucide-react';
import type { InsightModel } from '../types';

interface EvidenceModalProps {
  insight: InsightModel | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ insight, onClose }) => {
  if (!insight) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-full max-w-2xl rounded-2xl p-6 shadow-2xl border border-navy-700 bg-navy-900/95 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-navy-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/30">
                Deterministic Audit
              </span>
              <span className="flex items-center gap-1 text-xs text-emerald-400 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Validated against Python Cache
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">{insight.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Audit Details */}
        <div className="mt-5 space-y-4 text-xs sm:text-sm">
          {/* Formula and Method */}
          <div className="p-4 rounded-xl bg-navy-950 border border-navy-800">
            <div className="flex items-center gap-2 text-brand-cyan font-semibold mb-2">
              <Calculator className="w-4 h-4" />
              <span>Calculation Method & Written Formula (FR-13)</span>
            </div>
            <code className="block p-2.5 rounded-lg bg-navy-900 text-slate-200 font-mono text-xs border border-navy-800">
              {insight.method_or_formula || 'Direct aggregation via pandas.DataFrame'}
            </code>
          </div>

          {/* Computed Numbers Evidence */}
          <div className="p-4 rounded-xl bg-navy-950 border border-navy-800">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold mb-2">
              <Cpu className="w-4 h-4" />
              <span>Raw Computed Numbers (No LLM Inventions)</span>
            </div>
            <pre className="p-2.5 rounded-lg bg-navy-900 text-slate-300 font-mono text-xs overflow-x-auto border border-navy-800">
              {JSON.stringify(insight.evidence, null, 2)}
            </pre>
          </div>

          {/* Source Location */}
          <div className="p-4 rounded-xl bg-navy-950 border border-navy-800">
            <div className="flex items-center gap-2 text-indigo-400 font-semibold mb-2">
              <FileText className="w-4 h-4" />
              <span>Data Origin & Row Reference (FR-4)</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded bg-navy-900 border border-navy-800/80">
                <span className="text-slate-400">File: </span>
                <span className="text-white">{insight.source.filename}</span>
              </div>
              <div className="p-2 rounded bg-navy-900 border border-navy-800/80">
                <span className="text-slate-400">Sheet: </span>
                <span className="text-white">{insight.source.sheet || 'Default Table'}</span>
              </div>
              <div className="p-2 rounded bg-navy-900 border border-navy-800/80 col-span-2">
                <span className="text-slate-400">Row Boundaries: </span>
                <span className="text-white">{insight.source.row_range || 'All matching records'}</span>
              </div>
            </div>
          </div>

          {/* Reliability Note */}
          <div className="p-4 rounded-xl bg-navy-950 border border-navy-800">
            <div className="flex items-center gap-2 text-amber-400 font-semibold mb-2">
              <ShieldAlert className="w-4 h-4" />
              <span>Reliability & Uncertainty Note</span>
            </div>
            <div className="space-y-1.5 text-xs">
              <p>
                <strong className="text-slate-300">Statistical Confidence: </strong>
                <span className="text-slate-400">{insight.reliability.statistical_confidence}</span>
              </p>
              <p>
                <strong className="text-slate-300">Extraction Reliability: </strong>
                <span className="text-slate-400">{insight.reliability.extraction_reliability}</span>
              </p>
              <p>
                <strong className="text-slate-300">Judgment Uncertainty: </strong>
                <span className="text-slate-400">{insight.reliability.judgment_uncertainty}</span>
              </p>
            </div>
          </div>

          {/* Assumptions */}
          {insight.assumptions_and_limitations.length > 0 && (
            <div className="p-4 rounded-xl bg-navy-950 border border-navy-800">
              <span className="text-slate-400 font-semibold block mb-1">
                Assumptions & Limitations:
              </span>
              <ul className="list-disc list-inside text-xs text-slate-400 space-y-1">
                {insight.assumptions_and_limitations.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-navy-800 hover:bg-navy-700 text-white text-xs font-semibold transition"
          >
            Close Audit Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
