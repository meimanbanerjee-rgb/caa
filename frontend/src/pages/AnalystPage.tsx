// frontend/src/pages/AnalystPage.tsx
// Grounded Infosys AI Analyst Chat grounded in verified Python computations.
// Includes direct dataset upload zone, instant prompt chips, and evidence citations.

import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  ShieldCheck,
  Bot,
  User,
  UploadCloud,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';
import { ChartCard } from '../components/ChartCard';
import type { AnalysisModel, ChatMessage, HealthStatus, PageId } from '../types';
import type { ThemeConfig } from '../types/theme';

interface AnalystPageProps {
  analyses: AnalysisModel[];
  selectedAnalysis: AnalysisModel | null;
  onSelectAnalysis: (analysis: AnalysisModel) => void;
  health: HealthStatus | null;
  onNavigate?: (page: PageId) => void;
  theme: ThemeConfig;
  onUploadAndAnalyze?: (file: File) => void;
  isAnalyzing?: boolean;
}

export const AnalystPage: React.FC<AnalystPageProps> = ({
  analyses,
  selectedAnalysis,
  onSelectAnalysis,
  health,
  theme,
  onUploadAndAnalyze,
  isAnalyzing,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const analysis = selectedAnalysis || (analyses.length > 0 ? analyses[0] : null);

  useEffect(() => {
    if (analysis) {
      loadHistory(analysis.id);
    }
  }, [analysis?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const loadHistory = async (analysisId: string) => {
    try {
      const history = await api.getChatHistory(analysisId);
      if (history.length > 0) {
        setMessages(history);
      } else {
        // Starter greeting
        setMessages([
          {
            role: 'analyst',
            text: `Hello! I am your Infosys AI Grounded Business Analyst. I answer questions strictly using verified pandas calculations for this dataset. The AI will never invent numbers or guess uncalculated metrics. What would you like to explore?`,
            timestamp: new Date().toISOString(),
            sources: analysis ? analysis.dataset_ids.map((d) => `dataset:${d}`) : [],
            limitations: ['Grounded mode active: Answers cite deterministic results only.'],
          },
        ]);
      }
    } catch {
      // ignore
    }
  };

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputText;
    if (!textToSend.trim() || !analysis || loading) return;

    const userQuery = textToSend.trim();
    setInputText('');
    setLoading(true);

    const tempUserMsg: ChatMessage = {
      role: 'user',
      text: userQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await api.sendChatMessage(analysis.id, userQuery);
      setMessages((prev) => [...prev, res.message]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'analyst',
          text: `Error contacting analysis service: ${err.message}`,
          timestamp: new Date().toISOString(),
          limitations: ['Network error / backend service communication failure'],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

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
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0 && onUploadAndAnalyze) {
      onUploadAndAnalyze(e.dataTransfer.files[0]);
    }
  };

  const promptSuggestions: string[] =
    analysis?.metrics?.suggested_questions && analysis.metrics.suggested_questions.length > 0
      ? analysis.metrics.suggested_questions
      : [
          'What is our total revenue and gross profit margin?',
          'Which products generate the most profit?',
          'Which region has the highest revenue?',
          'Show monthly revenue trend.',
          'What is the average order value?',
        ];

  return (
    <div className="max-w-5xl mx-auto space-y-4 animate-fade-in flex flex-col h-[calc(100vh-100px)] select-none">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.tsv,.xlsx,.json,.jsonl,.pdf,.txt"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0 && onUploadAndAnalyze) {
            onUploadAndAnalyze(e.target.files[0]);
          }
          if (fileInputRef.current) fileInputRef.current.value = '';
        }}
        className="hidden"
      />

      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase font-bold text-slate-400">
              Infosys AI Consultation
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Safe Plans Only (FR-18)
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white mt-0.5">
            Grounded Business Analyst
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {health?.ai_configured && (
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Groq {health.model}</span>
            </div>
          )}

          {/* Dataset Switcher */}
          {analyses.length > 1 && (
            <select
              value={analysis?.id || ''}
              onChange={(e) => {
                const found = analyses.find((a) => a.id === e.target.value);
                if (found) onSelectAnalysis(found);
              }}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none"
            >
              {analyses.map((a) => {
                const label = a.metrics?.dataset_name || `Dataset ${a.id.slice(0, 8)}`;
                const rev = a.metrics?.net_sales ?? a.metrics?.total_revenue;
                return (
                  <option key={a.id} value={a.id}>
                    {label} {rev ? `($${Number(rev).toLocaleString()})` : ''}
                  </option>
                );
              })}
            </select>
          )}

          {/* Quick Upload Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isAnalyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white shadow transition hover:opacity-95"
            style={{ backgroundColor: theme.primary }}
          >
            {isAnalyzing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <UploadCloud className="w-3.5 h-3.5" />
            )}
            <span>{isAnalyzing ? 'Analyzing...' : '+ Upload Dataset'}</span>
          </button>
        </div>
      </div>

      {/* When NO dataset is loaded yet, show Hero Drag & Drop Zone */}
      {!analysis ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`dash-card border-2 border-dashed rounded-3xl p-10 text-center cursor-pointer transition-all duration-200 my-auto ${
            isDragging
              ? 'border-white bg-slate-800/80 scale-[1.01]'
              : 'border-slate-750 hover:border-slate-600 bg-slate-900/60'
          }`}
          style={isDragging ? { borderColor: theme.primary } : undefined}
        >
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-white shadow-xl"
            style={{ backgroundColor: theme.primary }}
          >
            {isAnalyzing ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>
          <h2 className="text-xl font-bold text-white">
            {isAnalyzing ? 'Analyzing Dataset...' : 'Give Your Dataset to Infosys AI'}
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
            Drop your CSV, Excel (.xlsx), JSON, or PDF file here to automatically compute metrics and begin chatting with the AI Analyst.
          </p>
          <button
            type="button"
            className="mt-5 px-5 py-2.5 rounded-xl text-xs font-bold text-white shadow-lg transition hover:opacity-95"
            style={{ backgroundColor: theme.primary }}
          >
            Browse Dataset Files
          </button>
        </div>
      ) : (
        <>
          {/* Chat Messages Window */}
          <div className="flex-1 overflow-y-auto space-y-3.5 p-4 rounded-2xl dash-card border border-slate-800 bg-[#0d121d]">
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={idx}
                  className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                      isUser ? 'bg-slate-700 text-slate-100' : 'text-white'
                    }`}
                    style={!isUser ? { backgroundColor: theme.primary } : undefined}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className={`max-w-[85%] sm:max-w-[75%] space-y-2`}>
                    <div
                      className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                        isUser
                          ? 'bg-slate-800 text-slate-100 border border-slate-700 rounded-tr-none'
                          : 'dash-card text-slate-200 border border-slate-750 rounded-tl-none shadow-md'
                      }`}
                    >
                      <div className="whitespace-pre-wrap font-sans">{msg.text}</div>
                    </div>

                    {/* Interactive Chart Rendering (FR-14, FR-18) */}
                    {!isUser && msg.chart_payload && msg.chart_payload.data && msg.chart_payload.data.length > 0 && (
                      <div className="rounded-2xl overflow-hidden border border-slate-750 bg-slate-900/90 p-2 shadow-lg">
                        <ChartCard
                          title={msg.chart_payload.title}
                          type={msg.chart_payload.type}
                          data={msg.chart_payload.data}
                          xKey={msg.chart_payload.x_key}
                          yKey={msg.chart_payload.y_key}
                        />
                      </div>
                    )}

                    {/* Formatted Financial Table Rendering */}
                    {!isUser && msg.table_payload && msg.table_payload.length > 0 && (() => {
                      const tableRows = msg.table_payload;
                      const headers = Object.keys(tableRows[0] || {})
                        .filter((k) => k !== 'metric' && !k.startsWith('_'))
                        .slice(0, 6);
                      return (
                        <div className="overflow-x-auto rounded-2xl border border-slate-750 bg-slate-900/90 p-3 shadow-lg">
                          <table className="w-full text-left text-[11px] font-mono">
                            <thead>
                              <tr className="border-b border-slate-750 text-slate-400">
                                {headers.map((key) => (
                                  <th key={key} className="py-1.5 px-2.5 uppercase font-semibold">
                                    {key.replace(/_/g, ' ')}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {tableRows.slice(0, 8).map((row, rIdx) => (
                                <tr key={rIdx} className="border-b border-slate-800/40 hover:bg-slate-800/40 transition">
                                  {headers.map((key) => {
                                    const val = row[key];
                                    const isNumeric = typeof val === 'number';
                                    const formatted =
                                      isNumeric && (key.includes('sales') || key.includes('profit') || key.includes('cost') || key.includes('value'))
                                        ? `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                        : isNumeric && (key.includes('margin') || key.includes('pct') || key.includes('share') || key.includes('percentage'))
                                        ? `${val.toFixed(2)}%`
                                        : String(val ?? '');
                                    return (
                                      <td key={key} className="py-1.5 px-2.5 text-slate-200">
                                        {formatted}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      );
                    })()}

                    {/* Sources and Reliability Notes (FR-17, FR-21) */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 px-1">
                        <span className="text-[10px] text-slate-500 font-mono">Sources:</span>
                        {msg.sources.map((s, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    )}

                    {!isUser && msg.limitations && msg.limitations.length > 0 && (
                      <div className="text-[10px] text-slate-500 font-mono px-1 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span>{msg.limitations[0]}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-start gap-3">
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm"
                  style={{ backgroundColor: theme.primary }}
                >
                  <Bot className="w-4 h-4" />
                </div>
                <div className="dash-card p-3 rounded-2xl border border-slate-750 flex items-center gap-2 text-xs text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin text-slate-300" />
                  <span>Infosys AI Analyst verifying computations via Groq LLaMA...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Suggestions */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 shrink-0 scrollbar-none">
            <span className="text-[10px] uppercase font-bold text-slate-500 font-mono shrink-0">
              Suggested:
            </span>
            {promptSuggestions.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                disabled={loading}
                className="px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-medium shrink-0 transition hover:text-white"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Chat Input Field */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 shrink-0 pb-1"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask a question about this dataset (e.g. revenue, margins, anomalies)..."
              disabled={loading}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700 transition"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || loading}
              className="px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow transition disabled:opacity-50 hover:opacity-95 flex items-center gap-1.5"
              style={{ backgroundColor: theme.primary }}
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
          </form>
        </>
      )}
    </div>
  );
};
