// frontend/src/components/Sidebar.tsx
// Modern vertical sidebar for Infosys AI with grouped navigation and prominent Ask AI chat.

import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  TableProperties,
  MessageSquareCode,
  FileSpreadsheet,
  History,
  Palette,
  ChevronsLeft,
  ChevronsRight,
  Flame,
  Zap,
} from 'lucide-react';
import type { PageId } from '../types';
import type { ThemeConfig } from '../types/theme';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  theme: ThemeConfig;
  onOpenThemeModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  collapsed,
  onToggleCollapse,
  theme,
  onOpenThemeModal,
}) => {
  const analyticsItems = [
    { id: 'insights' as PageId, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'explorer' as PageId, label: 'Data Explorer', icon: TableProperties },
    { id: 'reports' as PageId, label: 'Reports', icon: FileSpreadsheet },
  ];

  const aiItems = [
    { id: 'analyst' as PageId, label: 'Ask AI Chat', icon: MessageSquareCode, badge: 'BETA' },
    { id: 'insights' as PageId, label: 'Anomaly Detection', icon: Flame },
  ];

  const dataItems = [
    { id: 'upload' as PageId, label: 'Data Sources', icon: UploadCloud },
    { id: 'history' as PageId, label: 'Audit Archive', icon: History },
  ];

  const renderGroup = (title: string, items: typeof analyticsItems) => (
    <div className="space-y-1 py-1.5">
      {!collapsed && (
        <div className="px-3 pb-1 text-[10px] font-bold tracking-wider uppercase text-slate-500 font-mono">
          {title}
        </div>
      )}
      {items.map((item, idx) => {
        const isActive = currentPage === item.id;
        const Icon = item.icon;
        return (
          <button
            key={`${item.id}-${idx}`}
            onClick={() => onSelectPage(item.id)}
            title={collapsed ? item.label : undefined}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150 relative group ${
              isActive
                ? `${theme.accentBg} ${theme.accentText} border ${theme.accentBorder} shadow-sm`
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/40'
            }`}
          >
            <Icon
              className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-105 ${
                isActive ? theme.accentText : 'text-slate-400 group-hover:text-slate-200'
              }`}
            />
            {!collapsed && (
              <span className="flex-1 text-left truncate">{item.label}</span>
            )}
            {!collapsed && (item as any).badge && (
              <span
                className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shadow-sm"
                style={{
                  backgroundColor: `${theme.primary}25`,
                  color: theme.primary,
                  border: `1px solid ${theme.primary}50`,
                }}
              >
                {(item as any).badge}
              </span>
            )}
            {/* Active left indicator */}
            {isActive && (
              <span
                className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r"
                style={{ backgroundColor: theme.primary }}
              />
            )}
          </button>
        );
      })}
    </div>
  );

  return (
    <aside
      className={`dash-card flex flex-col justify-between border-r border-slate-800/80 transition-all duration-200 z-30 select-none ${
        collapsed ? 'w-16' : 'w-56'
      } shrink-0 min-h-screen bg-[#0a0e17]`}
    >
      <div>
        {/* Brand Header */}
        <div className="h-14 px-4 border-b border-slate-800/70 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-lg transition-colors"
              style={{
                backgroundColor: theme.primary,
                boxShadow: `0 0 14px ${theme.glowColor}`,
              }}
            >
              <Zap className="w-4 h-4 text-white fill-white" />
            </div>
            {!collapsed && (
              <div className="leading-tight truncate">
                <span className="text-sm font-extrabold tracking-tight text-white font-mono block">
                  Infosys <span style={{ color: theme.primary }}>AI</span>
                </span>
                <span className="text-[10px] text-slate-400 font-sans block">
                  Business Intelligence
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Grouped Navigation */}
        <div className="p-2 space-y-1">
          {renderGroup('Analytics', analyticsItems)}
          {renderGroup('AI & Insights', aiItems)}
          {renderGroup('Data Management', dataItems)}
        </div>
      </div>

      {/* Footer Controls */}
      <div className="p-2 border-t border-slate-800/70 space-y-1">
        <button
          onClick={onOpenThemeModal}
          title="Toggle Color Theme"
          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition"
        >
          <Palette className="w-4 h-4 shrink-0 text-slate-400" />
          {!collapsed && (
            <div className="flex-1 flex items-center justify-between">
              <span>Theme Palette</span>
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: theme.primary }}
              />
            </div>
          )}
        </button>

        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:text-slate-300 hover:bg-slate-800/40 transition"
        >
          {collapsed ? (
            <ChevronsRight className="w-4 h-4 mx-auto" />
          ) : (
            <>
              <ChevronsLeft className="w-4 h-4" />
              <span>Collapse Sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
