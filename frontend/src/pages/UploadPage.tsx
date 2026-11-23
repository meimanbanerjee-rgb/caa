// frontend/src/pages/UploadPage.tsx
// Upload workspace with 1-click auto-analysis, drag-and-drop, format validation, and direct AI pipeline.

import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  Trash2,
  TableProperties,
  ShieldCheck,
  FileCode,
  FileText,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { api } from '../api/client';
import type { DatasetModel, PageId } from '../types';
import type { ThemeConfig } from '../types/theme';

interface UploadPageProps {
  datasets: DatasetModel[];
  onRefreshDatasets: () => void;
  onNavigate: (page: PageId) => void;
  onSelectDatasetForExplorer: (dataset: DatasetModel) => void;
  onUploadAndAnalyze?: (file: File) => void;
  onAnalyzeExisting?: (datasetId: string) => void;
  isAnalyzing?: boolean;
  theme?: ThemeConfig;
}

export const UploadPage: React.FC<UploadPageProps> = ({
  datasets,
  onRefreshDatasets,
  onNavigate,
  onSelectDatasetForExplorer,
  onUploadAndAnalyze,
  onAnalyzeExisting,
  isAnalyzing,
  theme,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadWarnings, setUploadWarnings] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const primaryColor = theme?.primary || '#f97316';

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (onUploadAndAnalyze) {
        onUploadAndAnalyze(file);
      } else {
        handleFiles(Array.from(e.dataTransfer.files));
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (onUploadAndAnalyze) {
        onUploadAndAnalyze(file);
      } else {
        handleFiles(Array.from(e.target.files));
      }
    }
  };

  const handleFiles = async (files: File[]) => {
    setUploading(true);
    setErrorMessage(null);
    setUploadWarnings([]);

    try {
      const res = await api.uploadFiles(files);
      if (res.warnings && res.warnings.length > 0) {
        setUploadWarnings(res.warnings);
      }
      onRefreshDatasets();
    } catch (err: any) {
      setErrorMessage(err.message || 'File upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete "${name}"?`)) {
      try {
        await api.deleteDataset(id);
        onRefreshDatasets();
      } catch (err: any) {
        alert(`Failed to delete dataset: ${err.message}`);
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'csv':
      case 'tsv':
        return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
      case 'xlsx':
        return <FileSpreadsheet className="w-5 h-5 text-teal-400" />;
      case 'json':
      case 'jsonl':
        return <FileCode className="w-5 h-5 text-purple-400" />;
      case 'pdf':
        return <FileText className="w-5 h-5 text-rose-400" />;
      default:
        return <FileSpreadsheet className="w-5 h-5 text-blue-400" />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl mx-auto pb-10">
      {/* Title & Instructions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400">Data Management</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              1-Step Auto-Analysis
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">Dataset Sources & Upload</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Give your dataset file to Infosys AI for automated pandas analytics, anomaly detection, and grounded executive insights.
          </p>
        </div>
      </div>

      {/* Drag & Drop Hero Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`dash-card border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-white bg-slate-800/80 scale-[1.01]'
            : 'border-slate-750 hover:border-slate-600 bg-slate-900/60'
        }`}
        style={isDragging ? { borderColor: primaryColor } : undefined}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept=".csv,.tsv,.xlsx,.json,.jsonl,.pdf,.txt"
          className="hidden"
        />

        <div
          className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-white shadow-xl"
          style={{ backgroundColor: primaryColor }}
        >
          {isAnalyzing || uploading ? (
            <Loader2 className="w-8 h-8 animate-spin" />
          ) : (
            <UploadCloud className="w-8 h-8" />
          )}
        </div>

        <h3 className="text-lg font-bold text-white">
          {isAnalyzing
            ? 'Running Pandas Analytics & Generating AI Insights...'
            : uploading
            ? 'Validating & Storing Dataset...'
            : 'Drop your dataset file here to analyze immediately'}
        </h3>
        <p className="mt-1.5 text-xs sm:text-sm text-slate-400">
          or <span className="font-semibold underline text-white">click to browse files</span> on your computer
        </p>

        {/* Format Badges */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {['CSV', 'TSV', 'Excel (.xlsx)', 'JSON', 'JSONL', 'PDF', 'TXT'].map((fmt) => (
            <span
              key={fmt}
              className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono border border-slate-700"
            >
              {fmt}
            </span>
          ))}
          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-mono border border-emerald-500/20">
            Max 25MB
          </span>
        </div>

        <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Automated pipeline: uploads file, calculates metrics with pandas, and populates Infosys AI Dashboard.</span>
        </div>
      </div>

      {/* Error & Warning Messages */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300 text-xs sm:text-sm">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold">Upload Error</h4>
            <p className="mt-0.5 text-rose-200">{errorMessage}</p>
          </div>
        </div>
      )}

      {uploadWarnings.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-amber-300 font-bold">
            <AlertCircle className="w-4 h-4" />
            <span>Upload Notices:</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-amber-200">
            {uploadWarnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Available Datasets Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
            Available Datasets ({datasets.length})
          </h2>
          <span className="text-xs text-slate-500">Stored safely in local sqlite database</span>
        </div>

        {datasets.length === 0 ? (
          <div className="dash-card p-8 text-center rounded-2xl border border-slate-800 text-slate-400 text-xs">
            No files uploaded yet. Drag a test dataset (e.g. sales CSV) above to start.
          </div>
        ) : (
          <div className="space-y-2.5">
            {datasets.map((dataset) => (
              <div
                key={dataset.id}
                className="dash-card rounded-2xl p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-slate-800/80 flex items-center justify-center border border-slate-700 shrink-0">
                    {getFileIcon(dataset.file_type)}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-white truncate">{dataset.filename}</h3>
                    <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mt-0.5">
                      <span>{formatFileSize(dataset.size_bytes)}</span>
                      <span>•</span>
                      <span>{dataset.file_type.toUpperCase()}</span>
                      <span>•</span>
                      <span>{new Date(dataset.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                  {onAnalyzeExisting && (
                    <button
                      onClick={() => onAnalyzeExisting(dataset.id)}
                      disabled={isAnalyzing}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold text-white shadow transition hover:opacity-95"
                      style={{ backgroundColor: primaryColor }}
                      title="Run deterministic pandas calculations and open AI dashboard"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>⚡ Analyze with AI</span>
                    </button>
                  )}

                  <button
                    onClick={() => {
                      onSelectDatasetForExplorer(dataset);
                      onNavigate('explorer');
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium border border-slate-700 transition"
                  >
                    <TableProperties className="w-3.5 h-3.5 text-slate-300" />
                    <span>Explore Rows</span>
                  </button>

                  <button
                    onClick={() => handleDelete(dataset.id, dataset.filename)}
                    className="p-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
