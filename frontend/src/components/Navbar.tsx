// frontend/src/components/Navbar.tsx
// Top navigation bar showing brand, page tabs, backend health, and AI status pill.

import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  TableProperties,
  Sparkles,
  MessageSquareCode,
  FileSpreadsheet,
  History,
  Activity,
  Cpu,
  ShieldCheck,
} from 'lucide-react';
import type { HealthStatus, PageId } from '../types';

interface NavbarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  health: HealthStatus | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentPage,
  onSelectPage,
  health,
  healthLoading,
  onRefreshHealth,
}) => {
  const navItems: { id: PageId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'upload', label: 'Upload Workspace', icon: <UploadCloud className="w-4 h-4" /> },
    { id: 'explorer', label: 'Data Explorer', icon: <TableProperties className="w-4 h-4" /> },
    { id: 'insights', label: 'Insights Dashboard', icon: <Sparkles className="w-4 h-4" /> },
    { id: 'analyst', label: 'AI Analyst', icon: <MessageSquareCode className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports & Export', icon: <FileSpreadsheet className="w-4 h-4" /> },
    { id: 'history', label: 'History', icon: <History className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-navy-800/80 px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 ring-1 ring-white/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white bg-clip-text">
                InsightForge <span className="text-brand-cyan">AI</span>
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-blue-500/10 text-brand-cyan border border-brand-cyan/20">
                v1.0 PRD
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono hidden sm:block">
              Rule 1: Python calculates. AI explains.
            </p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex items-center gap-1 overflow-x-auto py-1 scrollbar-none">
          {navItems.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onSelectPage(item.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs md:text-sm font-medium transition-all duration-150 whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600/20 text-brand-cyan border border-brand-cyan/30 shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-navy-800/60'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System & AI status pills */}
        <div className="flex items-center gap-2 text-xs">
          {/* Backend Status Pill */}
          <button
            onClick={onRefreshHealth}
            title="Click to re-verify backend health"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-navy-900 border border-navy-800 hover:border-slate-600 transition"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                health?.status === 'healthy'
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-rose-500'
              }`}
            />
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-mono text-slate-300">
              {healthLoading
                ? 'Checking...'
                : health?.status === 'healthy'
                ? 'FastAPI Online'
                : 'Offline'}
            </span>
          </button>

          {/* AI Key Status Pill */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono ${
              health?.ai_configured
                ? 'bg-blue-500/10 text-blue-300 border-blue-500/30'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
            }`}
            title={
              health?.ai_configured
                ? `Provider active: ${health.provider}`
                : 'Deterministic local fallback active (No key required for full analytics)'
            }
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>
              {health?.ai_configured
                ? `AI: ${health.provider}`
                : 'AI: Deterministic Fallback'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
