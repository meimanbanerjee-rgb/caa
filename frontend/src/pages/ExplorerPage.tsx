// frontend/src/pages/ExplorerPage.tsx
// Data Explorer page showing schema profiles, suggested semantic meanings, quality checks, and sample tables.

import React, { useState } from 'react';
import {
  TableProperties,
  CheckCircle2,
  AlertTriangle,
  History,
  Play,
  Layers,
  Check,
} from 'lucide-react';
import { api } from '../api/client';
import type { DatasetModel, PageId } from '../types';

interface ExplorerPageProps {
  datasets: DatasetModel[];
  selectedDataset: DatasetModel | null;
  onSelectDataset: (dataset: DatasetModel) => void;
  onNavigate: (page: PageId) => void;
  onAnalysisGenerated: () => void;
}

export const ExplorerPage: React.FC<ExplorerPageProps> = ({
  datasets,
  selectedDataset,
  onSelectDataset,
  onNavigate,
  onAnalysisGenerated,
}) => {
  const [activeTab, setActiveTab] = useState<'schema' | 'sample' | 'transformations'>('schema');
  const [analyzing, setAnalyzing] = useState(false);
  const [editingColumn, setEditingColumn] = useState<string | null>(null);
  const [selectedMeaning, setSelectedMeaning] = useState<string>('');
  const [selectedTableIndex, setSelectedTableIndex] = useState<number>(0);

  const dataset = selectedDataset || (datasets.length > 0 ? datasets[0] : null);
  const table = dataset && dataset.tables.length > selectedTableIndex
    ? dataset.tables[selectedTableIndex]
    : (dataset?.tables[0] || null);

  const handleConfirmMeaning = async (columnName: string, meaning: string) => {
    if (!dataset) return;
    try {
      const updated = await api.updateFieldMeaning(dataset.id, columnName, meaning);
      onSelectDataset(updated);
      setEditingColumn(null);
    } catch (err: any) {
      alert(`Failed to update field: ${err.message}`);
    }
  };

  const handleRunAnalysis = async () => {
    if (!dataset) return;
    setAnalyzing(true);
    try {
      await api.runAnalysis(dataset.id);
      onAnalysisGenerated();
      onNavigate('insights');
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  if (!dataset) {
    return (
      <div className="p-12 text-center rounded-3xl glass-panel max-w-xl mx-auto my-12 border border-navy-800">
        <TableProperties className="w-12 h-12 text-slate-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-white">No Dataset Selected</h2>
        <p className="mt-1 text-xs text-slate-400">
          Upload a spreadsheet or dataset first to inspect schemas and quality metrics.
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

  return (
    <div className="space-y-6 animate-fade-in max-w-6xl mx-auto">
      {/* Top Header & Dataset Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-navy-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase text-brand-cyan tracking-wider font-semibold">
              Data Profiler
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-400">
              FR-7 & FR-8 Schema Inspection
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-white mt-1">{dataset.filename}</h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Dataset Switcher */}
          {datasets.length > 1 && (
            <select
              value={dataset.id}
              onChange={(e) => {
                const found = datasets.find((d) => d.id === e.target.value);
                if (found) onSelectDataset(found);
              }}
              className="px-3 py-2 rounded-xl bg-navy-850 text-slate-200 text-xs font-medium border border-navy-750 focus:outline-none focus:border-brand-cyan"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>
          )}

          {/* Trigger Analysis Button */}
          <button
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-500/20 transition disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{analyzing ? 'Running Calculations...' : 'Run Analytics Engine'}</span>
          </button>
        </div>
      </div>

      {/* Multi-sheet / Multi-table Switcher */}
      {dataset.tables.length > 1 && (
        <div className="flex items-center gap-2 p-2 rounded-2xl glass-panel border border-navy-800">
          <span className="text-xs font-mono text-slate-400 pl-2">Sheets:</span>
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {dataset.tables.map((tbl, idx) => (
              <button
                key={tbl.id}
                onClick={() => setSelectedTableIndex(idx)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition ${
                  selectedTableIndex === idx
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-navy-850 text-slate-300 hover:text-white border border-navy-750'
                }`}
              >
                {tbl.name} ({tbl.row_count} rows, {tbl.column_count} cols)
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Tabs (Schema Profiling vs Sample Rows vs Transformations) */}
      <div className="flex items-center gap-2 border-b border-navy-800">
        <button
          onClick={() => setActiveTab('schema')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'schema'
              ? 'border-brand-cyan text-brand-cyan'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <TableProperties className="w-4 h-4" />
          <span>Column Types & Suggested Meanings</span>
        </button>

        <button
          onClick={() => setActiveTab('sample')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'sample'
              ? 'border-brand-cyan text-brand-cyan'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Data Preview & Samples</span>
        </button>

        <button
          onClick={() => setActiveTab('transformations')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'transformations'
              ? 'border-brand-cyan text-brand-cyan'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Transformation Audit Log</span>
        </button>
      </div>

      {/* Tab 1: Column Schema and Semantic Profiling */}
      {activeTab === 'schema' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-navy-900/60 border border-navy-800 text-xs text-slate-300 flex items-center justify-between">
            <div>
              <strong className="text-white">FR-8 Semantic Suggestion Rule: </strong>
              Columns are tagged automatically based on column headers and value patterns. Click any
              field to confirm or change its business role before analytical computation.
            </div>
          </div>

          <div className="glass-panel rounded-2xl overflow-hidden border border-navy-800">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-navy-900/80 text-slate-400 uppercase font-mono text-[11px] border-b border-navy-800">
                  <tr>
                    <th className="p-4">Column Name</th>
                    <th className="p-4">Detected Type</th>
                    <th className="p-4">Inferred Business Meaning</th>
                    <th className="p-4">Quality Status</th>
                    <th className="p-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-800/80 text-slate-200">
                  {!table || table.columns.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-slate-400">
                        Initial file parsed. Click "Run Analytics Engine" to profile columns and compute metrics.
                      </td>
                    </tr>
                  ) : (
                    table.columns.map((col) => (
                      <tr key={col.name} className="hover:bg-navy-850/50 transition">
                        <td className="p-4 font-mono font-medium text-white">{col.name}</td>
                        <td className="p-4">
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-navy-800 text-slate-300 border border-navy-750">
                            {col.detected_type}
                          </span>
                        </td>
                        <td className="p-4">
                          {editingColumn === col.name ? (
                            <div className="flex items-center gap-2">
                              <select
                                value={selectedMeaning || col.suggested_meaning || 'general'}
                                onChange={(e) => setSelectedMeaning(e.target.value)}
                                className="px-2 py-1 rounded bg-navy-950 text-white text-xs border border-navy-700"
                              >
                                <option value="revenue">revenue</option>
                                <option value="cost">cost</option>
                                <option value="margin">margin</option>
                                <option value="order_date">order_date</option>
                                <option value="customer_id">customer_id</option>
                                <option value="category">category</option>
                                <option value="units_sold">units_sold</option>
                                <option value="general">general text</option>
                              </select>
                              <button
                                onClick={() => handleConfirmMeaning(col.name, selectedMeaning || 'general')}
                                className="p-1 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-brand-cyan">
                                {col.suggested_meaning || 'Unassigned'}
                              </span>
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                                  col.meaning_status === 'confirmed'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                }`}
                              >
                                {col.meaning_status}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="p-4">
                          {col.quality_stats.null_count > 0 ? (
                            <span className="text-amber-400 flex items-center gap-1 font-mono">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              {col.quality_stats.null_count} nulls ({col.quality_stats.null_percentage}%)
                            </span>
                          ) : (
                            <span className="text-emerald-400 flex items-center gap-1 font-mono">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              100% Complete
                            </span>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          <button
                            onClick={() => {
                              setEditingColumn(col.name);
                              setSelectedMeaning(col.suggested_meaning || 'general');
                            }}
                            className="text-slate-400 hover:text-white underline text-xs"
                          >
                            Edit Meaning
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Sample Rows */}
      {activeTab === 'sample' && (
        <div className="glass-panel rounded-2xl p-6 border border-navy-800">
          <div className="text-xs text-slate-400 mb-3 font-mono">
            Preview of parsed records (Read values only; no formula execution):
          </div>
          {!table || table.sample_rows.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No sample rows loaded.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs divide-y divide-navy-800">
                <thead className="bg-navy-900 text-slate-400 font-mono">
                  <tr>
                    {Object.keys(table.sample_rows[0]).map((k) => (
                      <th key={k} className="p-3">
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-800/80 font-mono text-slate-300">
                  {table.sample_rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-navy-850/40">
                      {Object.values(row).map((val: any, cidx) => (
                        <td key={cidx} className="p-3">
                          {String(val ?? 'NULL')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Transformation Log */}
      {activeTab === 'transformations' && (
        <div className="glass-panel rounded-2xl p-6 border border-navy-800 space-y-3">
          <div className="text-xs text-slate-400 font-mono">
            Audit log of all cleaning steps applied to this dataset:
          </div>
          {dataset.transformations.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-xs">
              Original data intact. No destructive cleaning performed yet.
            </div>
          ) : (
            <div className="space-y-2">
              {dataset.transformations.map((t, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-navy-900 border border-navy-800 text-xs font-mono text-slate-300"
                >
                  <span className="text-brand-cyan">Step {t.step}: </span>
                  <span>{t.action} on column [{t.column || 'dataset'}]</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
