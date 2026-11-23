// frontend/src/pages/ReportsPage.tsx
// Reports & Export page for downloading verifiable PDF reports and CSV datasets (PRD 5.6, FR-22, FR-23, FR-24).

import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Download,
  FileText,
  Calendar,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { api } from '../api/client';
import type { AnalysisModel, PageId, StructuredReport } from '../types';

interface ReportsPageProps {
  analyses: AnalysisModel[];
  selectedAnalysis: AnalysisModel | null;
  onSelectAnalysis: (analysis: AnalysisModel) => void;
  onNavigate: (page: PageId) => void;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({
  analyses,
  selectedAnalysis,
  onNavigate,
}) => {
  const analysis = selectedAnalysis || (analyses.length > 0 ? analyses[0] : null);
  const [reportData, setReportData] = useState<StructuredReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (analysis) {
      loadReport(analysis.id);
    }
  }, [analysis?.id]);

  const loadReport = async (analysisId: string) => {
    setLoading(true);
    try {
      const data = await api.getReportSections(analysisId);
      setReportData(data);
    } catch (err) {
      console.error('Failed to load report sections:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!analysis) {
    return (
      <div className="p-12 text-center rounded-3xl glass-panel max-w-xl mx-auto my-12 border border-navy-800">
        <FileSpreadsheet className="w-12 h-12 text-slate-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-white">No Reports Generated</h2>
        <p className="mt-1 text-xs text-slate-400">
          Run an analysis on an uploaded dataset to generate downloadable PDF reports and CSV tables.
        </p>
        <button
          onClick={() => onNavigate('upload')}
          className="mt-5 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition"
        >
          Go to Upload Workspace
        </button>
      </div>
    );
  }

  const pdfUrl = api.getPdfReportUrl(analysis.id);
  const csvUrl = api.getCsvReportUrl(analysis.id);

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-navy-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase text-brand-cyan tracking-wider font-semibold">
              Reporting & Exports
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-400">
              FR-22 & FR-24
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-white mt-1">Executive Report Center</h1>
        </div>

        {/* Download Buttons */}
        <div className="flex items-center gap-3">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            download
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-600/20 transition cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF Report</span>
          </a>

          <a
            href={csvUrl}
            download
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 text-xs font-bold border border-navy-700 transition cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Export CSV Metrics</span>
          </a>
        </div>
      </div>

      {/* Report Metadata Card */}
      <div className="glass-card rounded-2xl p-5 border border-navy-750 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-brand-cyan">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">InsightForge Comprehensive BI Report</h3>
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mt-0.5">
              <span>Analysis ID: {analysis.id}</span>
              <span>•</span>
              <span>Domain: {analysis.domain}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" />
            <span>{new Date(analysis.created_at).toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Audited & Verified</span>
          </div>
        </div>
      </div>

      {/* Live Report Section Preview (FR-22) */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-400">Building verified report preview...</div>
      ) : reportData ? (
        <div className="space-y-4">
          {reportData.sections.map((section) => (
            <div
              key={section.id}
              className="glass-panel rounded-2xl p-5 border border-navy-800 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-cyan" />
                  {section.title}
                </h3>
                <span className="text-[11px] text-slate-400 font-mono">{section.summary}</span>
              </div>

              {section.id === 'executive_summary' && section.content.points && (
                <div className="space-y-1.5 bg-blue-950/20 p-3.5 rounded-xl border border-blue-800/30">
                  {section.content.points.map((pt: string, idx: number) => (
                    <div key={idx} className="text-xs text-blue-200 flex items-start gap-2">
                      <span className="text-brand-cyan font-bold">•</span>
                      <span>{pt}</span>
                    </div>
                  ))}
                </div>
              )}

              {section.id === 'key_metrics' && section.items && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-navy-750 text-slate-400">
                        <th className="py-2 font-semibold">Metric</th>
                        <th className="py-2 font-semibold">Calculated Value</th>
                        <th className="py-2 font-semibold">Formula / Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-navy-800/50">
                      {section.items.map((it: any, idx: number) => (
                        <tr key={idx} className="hover:bg-navy-850/40">
                          <td className="py-2 text-slate-200 font-medium">{it.metric}</td>
                          <td className="py-2 text-brand-cyan font-mono font-bold">{it.value}</td>
                          <td className="py-2 text-slate-400 font-mono text-[11px]">{it.formula}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {section.id === 'risks' && section.items && (
                <div className="space-y-2">
                  {section.items.map((r: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-red-950/20 border border-red-800/30 flex items-start gap-2 text-xs">
                      <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-red-300">{r.type}: </span>
                        <span className="text-slate-300">{r.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {section.id === 'opportunities' && section.items && (
                <div className="space-y-2">
                  {section.items.map((opp: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/30 flex items-start gap-2 text-xs">
                      <Lightbulb className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-emerald-300">{opp.initiative}: </span>
                        <span className="text-slate-300">{opp.action}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};
