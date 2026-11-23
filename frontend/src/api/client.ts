// frontend/src/api/client.ts
// Unified HTTP API client for all backend calls.

import type {
  HealthStatus,
  DatasetModel,
  AnalysisModel,
  ChatMessage,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

class ApiClient {
  private base: string;

  constructor(baseUrl: string) {
    this.base = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.base}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        ...options,
      });

      if (!response.ok) {
        let errMessage = `HTTP error ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch {
          // ignore json parse error on response failure
        }
        throw new Error(errMessage);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      console.error(`API Request to ${endpoint} failed:`, err);
      throw err;
    }
  }

  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health');
  }

  async uploadFiles(files: File[]): Promise<{ datasets: DatasetModel[]; warnings: string[]; count: number }> {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    const url = `${this.base}/api/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }

    return response.json();
  }

  async listDatasets(): Promise<DatasetModel[]> {
    return this.request<DatasetModel[]>('/api/datasets');
  }

  async getDataset(id: string): Promise<DatasetModel> {
    return this.request<DatasetModel>(`/api/datasets/${id}`);
  }

  async updateFieldMeaning(datasetId: string, columnName: string, confirmedMeaning: string): Promise<DatasetModel> {
    return this.request<DatasetModel>(`/api/datasets/${datasetId}/fields`, {
      method: 'PATCH',
      body: JSON.stringify({ column_name: columnName, confirmed_meaning: confirmedMeaning }),
    });
  }

  async deleteDataset(id: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/api/datasets/${id}`, {
      method: 'DELETE',
    });
  }

  async runAnalysis(datasetId: string): Promise<AnalysisModel> {
    return this.request<AnalysisModel>(`/api/datasets/${datasetId}/analyze`, {
      method: 'POST',
    });
  }

  async getAnalysis(id: string): Promise<AnalysisModel> {
    return this.request<AnalysisModel>(`/api/analyses/${id}`);
  }

  async getInsightEvidence(analysisId: string, insightId: string): Promise<any> {
    return this.request<any>(`/api/analyses/${analysisId}/insights/${insightId}/evidence`);
  }

  async sendChatMessage(analysisId: string, question: string): Promise<{ message: ChatMessage; safe_plan_executed?: string }> {
    return this.request<any>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ analysis_id: analysisId, question }),
    });
  }

  async getChatHistory(analysisId: string): Promise<ChatMessage[]> {
    return this.request<ChatMessage[]>(`/api/chat/${analysisId}`);
  }

  async listHistory(): Promise<AnalysisModel[]> {
    return this.request<AnalysisModel[]>('/api/history');
  }

  async getReportSections(analysisId: string): Promise<any> {
    return this.request<any>(`/api/reports/${analysisId}/sections`);
  }

  getPdfReportUrl(analysisId: string): string {
    return `${this.base}/api/reports/${analysisId}/pdf`;
  }

  getCsvReportUrl(analysisId: string): string {
    return `${this.base}/api/reports/${analysisId}/csv`;
  }
}

export const api = new ApiClient(API_BASE);
