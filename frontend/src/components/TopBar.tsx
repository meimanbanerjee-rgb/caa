// frontend/src/components/TopBar.tsx
// Header bar for Infosys AI with direct file upload & analysis, search, theme switcher, and scope selector.

import React, { useState, useRef } from 'react';
import {
  Search,
  Calendar,
  ChevronDown,
  Check,
  UploadCloud,
  Loader2,
} from 'lucide-react';
import type { AnalysisModel, PageId } from '../types';
import type { ThemeConfig, ThemeId } from '../types/theme';
import { THEMES } from '../types/theme';

interface TopBarProps {
  analyses: AnalysisModel[];
  selectedAnalysis: AnalysisModel | null;
  onSelectAnalysis: (analysis: AnalysisModel) => void;
  onNavigate: (page: PageId) => void;
  theme: ThemeConfig;
  onSelectTheme: (themeId: ThemeId) => void;
  onUploadAndAnalyze?: (file: File) => void;
  isAnalyzing?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  analyses,
  selectedAnalysis,
  onSelectAnalysis,
  onNavigate,
  theme,
  onSelectTheme,
  onUploadAndAnalyze,
  isAnalyzing,
}) => {
  const [showScopeMenu, setShowScopeMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const currentAnalysis = selectedAnalysis || (analyses.length > 0 ? analyses[0] : null);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onNavigate('analyst');
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0 && onUploadAndAnalyze) {
      onUploadAndAnalyze(e.target.files[0]);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const themeList: ThemeId[] = ['solar', 'infosys', 'emerald', 'amethyst'];

  return (
    <header className="h-12 border-b border-slate-800/80 bg-[#0d121d] px-3.5 flex items-center justify-between gap-3 shrink-0 select-none">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.tsv,.xlsx,.json,.jsonl,.pdf,.txt"
        onChange={handleFileInput}
        className="hidden"
      />

      {/* Left: Scope Selector & Upload Button */}
      <div className="flex items-center gap-2">
        {/* Scope Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowScopeMenu(!showScopeMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-200 transition"
          >
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: theme.primary }} />
            <span className="truncate max-w-[130px] sm:max-w-[180px]">
              {currentAnalysis ? `${currentAnalysis.metrics?.dataset_name || 'Dataset'} View` : 'Executive View'}
            </span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {showScopeMenu && (
            <div className="absolute left-0 top-full mt-1.5 w-60 rounded-xl bg-slate-900 border border-slate-750 shadow-2xl p-1.5 z-50 text-xs">
              {analyses.length === 0 ? (
                <div className="px-2.5 py-2 text-slate-400 text-xs">No uploaded datasets yet</div>
              ) : (
                analyses.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => {
                      onSelectAnalysis(a);
                      setShowScopeMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between hover:bg-slate-800 transition ${
                      currentAnalysis?.id === a.id ? `${theme.accentText} font-bold` : 'text-slate-300'
                    }`}
                  >
                    <span className="truncate">{a.metrics?.dataset_name || a.id.slice(0, 8)}</span>
                    {currentAnalysis?.id === a.id && <Check className="w-3.5 h-3.5 shrink-0" />}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* DIRECT UPLOAD & ANALYZE BUTTON IN TOPBAR */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isAnalyzing}
          title="Upload CSV, Excel, JSON or PDF for automatic deterministic analysis"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white shadow-md transition disabled:opacity-50 hover:opacity-90"
          style={{
            backgroundColor: theme.primary,
            boxShadow: `0 0 12px ${theme.glowColor}`,
          }}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <UploadCloud className="w-3.5 h-3.5" />
              <span>+ Upload Dataset</span>
            </>
          )}
        </button>
      </div>

      {/* Center: Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-sm hidden md:block">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search metrics or ask AI... ⌘K"
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-8 pr-10 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700 transition"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.2 rounded bg-slate-800 text-[9px] font-mono text-slate-400 border border-slate-700">
            ⌘K
          </kbd>
        </div>
      </form>

      {/* Right Controls */}
      <div className="flex items-center gap-2 text-xs">
        {/* Instant Theme Palette Color Dots */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {themeList.map((tId) => {
            const t = THEMES[tId];
            const isSelected = theme.id === tId;
            return (
              <button
                key={tId}
                onClick={() => onSelectTheme(tId)}
                title={`Theme: ${t.name}`}
                className={`w-4 h-4 rounded-full transition-transform ${
                  isSelected ? 'scale-125 ring-2 ring-white/60' : 'opacity-60 hover:opacity-100 hover:scale-110'
                }`}
                style={{ backgroundColor: t.primary }}
              />
            );
          })}
        </div>

        {/* Date Filter */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 font-mono text-[11px]">
          <Calendar className="w-3.5 h-3.5" />
          <span>May 2026</span>
        </div>

        {/* User Avatar */}
        <div
          title="Infosys Enterprise User"
          className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-[11px] text-white shadow"
          style={{ backgroundColor: theme.primary }}
        >
          INF
        </div>
      </div>
    </header>
  );
};
