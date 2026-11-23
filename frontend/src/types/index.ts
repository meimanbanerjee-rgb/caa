// frontend/src/types/index.ts
// TypeScript interfaces mirroring backend Pydantic schemas.

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  ai_configured: boolean;
  provider: string;
  model: string;
  max_upload_mb: number;
}

export interface ColumnQualityStats {
  null_count: number;
  null_percentage: number;
  distinct_count: number;
  duplicate_count: number;
  min_value?: any;
  max_value?: any;
  mean_value?: number;
  outlier_count: number;
  warnings: string[];
}

export interface ColumnProfile {
  name: string;
  detected_type: string;
  suggested_meaning?: string;
  meaning_status: 'suggested' | 'confirmed';
  quality_stats: ColumnQualityStats;
}

export interface TableModel {
  id: string;
  dataset_id: string;
  name: string;
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
  sample_rows: Record<string, any>[];
}

export interface TransformationLog {
  step: number;
  timestamp: string;
  column?: string;
  action: string;
  before?: any;
  after?: any;
  row_reference?: string;
}

export interface DatasetModel {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
  tables: TableModel[];
  warnings: string[];
  transformations: TransformationLog[];
}

export interface SourceReference {
  filename: string;
  sheet?: string;
  row_range?: string;
  page?: number;
}

export interface ReliabilityNote {
  statistical_confidence: string;
  extraction_reliability: string;
  judgment_uncertainty: string;
}

export interface InsightModel {
  id: string;
  analysis_id: string;
  title: string;
  category: string;
  plain_english_explanation: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  observed_fact: string;
  interpretation: string;
  recommendation: string;
  evidence: Record<string, any>;
  method_or_formula: string;
  source: SourceReference;
  reliability: ReliabilityNote;
  assumptions_and_limitations: string[];
}

export interface AnalysisModel {
  id: string;
  dataset_ids: string[];
  domain: string;
  configuration: Record<string, any>;
  created_at: string;
  metrics: Record<string, any>;
  charts: any[];
  insights: InsightModel[];
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'analyst' | 'system';
  text: string;
  timestamp: string;
  computed_evidence?: Record<string, any>;
  sources?: string[];
  limitations?: string[];
  used_fallback?: boolean;
  table_payload?: any[];
  chart_payload?: {
    type: 'bar' | 'line';
    title: string;
    data: any[];
    x_key: string;
    y_key: string;
  };
}

export interface ReportSection {
  id: string;
  title: string;
  summary: string;
  content: Record<string, any>;
  items?: any[];
}

export interface StructuredReport {
  analysis_id: string;
  title: string;
  generated_at: string;
  domain: string;
  settings: Record<string, any>;
  sections: ReportSection[];
}

export type PageId =
  | 'overview'
  | 'upload'
  | 'explorer'
  | 'insights'
  | 'analyst'
  | 'reports'
  | 'history';
