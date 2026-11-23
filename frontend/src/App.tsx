// frontend/src/App.tsx
// Root application container for Infosys AI with auto-analysis upload, sidebar, topbar, and theme switcher.

import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { OverviewPage } from './pages/OverviewPage';
import { UploadPage } from './pages/UploadPage';
import { ExplorerPage } from './pages/ExplorerPage';
import { InsightsPage } from './pages/InsightsPage';
import { AnalystPage } from './pages/AnalystPage';
import { ReportsPage } from './pages/ReportsPage';
import { HistoryPage } from './pages/HistoryPage';
import { api } from './api/client';
import type { HealthStatus, DatasetModel, AnalysisModel, PageId } from './types';
import type { ThemeId } from './types/theme';
import { THEMES } from './types/theme';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('insights');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [currentThemeId, setCurrentThemeId] = useState<ThemeId>('solar');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [datasets, setDatasets] = useState<DatasetModel[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisModel[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetModel | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisModel | null>(null);

  // Auto-analysis state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null);

  const theme = THEMES[currentThemeId];

  // Fetch initial health and data
  useEffect(() => {
    refreshHealth();
    refreshData();
  }, []);

  const refreshHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.warn('Backend currently unreachable:', err);
      setHealth(null);
    }
  };

  const refreshData = async () => {
    try {
      const [dsList, anList] = await Promise.all([
        api.listDatasets().catch(() => []),
        api.listHistory().catch(() => []),
      ]);
      setDatasets(dsList);
      setAnalyses(anList);

      if (dsList.length > 0 && !selectedDataset) {
        setSelectedDataset(dsList[0]);
      }
      if (anList.length > 0 && !selectedAnalysis) {
        setSelectedAnalysis(anList[0]);
      }
    } catch {
      // ignore
    }
  };

  // Immediate 1-Step: Upload File -> Run Deterministic Analysis -> Populate Dashboard & AI
  const handleUploadAndAnalyze = async (file: File) => {
    setIsAnalyzing(true);
    setAnalysisStatus(`Uploading "${file.name}"...`);

    try {
      const uploadRes = await api.uploadFiles([file]);
      if (!uploadRes.datasets || uploadRes.datasets.length === 0) {
        throw new Error('Upload returned no valid dataset.');
      }
      const newDataset = uploadRes.datasets[0];

      setAnalysisStatus(`Executing pandas calculations on "${file.name}"...`);
      const newAnalysis = await api.runAnalysis(newDataset.id);

      setAnalysisStatus(`Generating AI insights and audit trail...`);

      // Update state
      setSelectedDataset(newDataset);
      setSelectedAnalysis(newAnalysis);
      setDatasets((prev) => [newDataset, ...prev.filter((d) => d.id !== newDataset.id)]);
      setAnalyses((prev) => [newAnalysis, ...prev.filter((a) => a.id !== newAnalysis.id)]);
      setCurrentPage('insights');
      setAnalysisStatus(null);
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
      setAnalysisStatus(null);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyzeExistingDataset = async (datasetId: string) => {
    setIsAnalyzing(true);
    setAnalysisStatus('Executing pandas calculations on selected dataset...');

    try {
      const newAnalysis = await api.runAnalysis(datasetId);
      setSelectedAnalysis(newAnalysis);
      setAnalyses((prev) => [newAnalysis, ...prev.filter((a) => a.id !== newAnalysis.id)]);
      const ds = datasets.find((d) => d.id === datasetId);
      if (ds) setSelectedDataset(ds);
      setCurrentPage('insights');
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
      setAnalysisStatus(null);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#090e17] text-slate-100 overflow-x-hidden font-sans">
      {/* 1. Left Vertical Sidebar (Collapsible) */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={setCurrentPage}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        theme={theme}
      />

      {/* 2. Main Content View Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Horizontal Header Bar */}
        <TopBar
          analyses={analyses}
          selectedAnalysis={selectedAnalysis}
          onSelectAnalysis={setSelectedAnalysis}
          onNavigate={setCurrentPage}
          theme={theme}
          onSelectTheme={setCurrentThemeId}
          onUploadAndAnalyze={handleUploadAndAnalyze}
          isAnalyzing={isAnalyzing}
        />

        {/* Dynamic Page Views */}
        <main className="flex-1 p-3 sm:p-4 lg:p-5 overflow-y-auto">
          {currentPage === 'insights' && (
            <InsightsPage
              analyses={analyses}
              selectedAnalysis={selectedAnalysis}
              onSelectAnalysis={setSelectedAnalysis}
              onNavigate={setCurrentPage}
              theme={theme}
              onUploadAndAnalyze={handleUploadAndAnalyze}
              isAnalyzing={isAnalyzing}
              analysisStatus={analysisStatus}
            />
          )}

          {currentPage === 'overview' && (
            <OverviewPage
              onNavigate={setCurrentPage}
              health={health}
              datasets={datasets}
              analyses={analyses}
            />
          )}

          {currentPage === 'upload' && (
            <UploadPage
              datasets={datasets}
              onRefreshDatasets={refreshData}
              onNavigate={setCurrentPage}
              onSelectDatasetForExplorer={setSelectedDataset}
              onUploadAndAnalyze={handleUploadAndAnalyze}
              onAnalyzeExisting={handleAnalyzeExistingDataset}
              isAnalyzing={isAnalyzing}
              theme={theme}
            />
          )}

          {currentPage === 'explorer' && (
            <ExplorerPage
              datasets={datasets}
              selectedDataset={selectedDataset}
              onSelectDataset={setSelectedDataset}
              onNavigate={setCurrentPage}
              onAnalysisGenerated={refreshData}
            />
          )}

          {currentPage === 'analyst' && (
            <AnalystPage
              analyses={analyses}
              selectedAnalysis={selectedAnalysis}
              onSelectAnalysis={setSelectedAnalysis}
              health={health}
              onNavigate={setCurrentPage}
              theme={theme}
              onUploadAndAnalyze={handleUploadAndAnalyze}
              isAnalyzing={isAnalyzing}
            />
          )}

          {currentPage === 'reports' && (
            <ReportsPage
              analyses={analyses}
              selectedAnalysis={selectedAnalysis}
              onSelectAnalysis={setSelectedAnalysis}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'history' && (
            <HistoryPage
              analyses={analyses}
              onSelectAnalysis={setSelectedAnalysis}
              onNavigate={setCurrentPage}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
