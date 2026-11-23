# backend/app/models/insight.py
# Pydantic schemas for insight objects, evidence traceability, and analysis jobs.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Pinpoints the origin file, sheet, and row numbers of extracted metrics."""
    filename: str
    sheet: Optional[str] = None
    row_range: Optional[str] = None
    page: Optional[int] = None


class ReliabilityNote(BaseModel):
    """Transparent reliability indicators separating statistical confidence and judgment."""
    statistical_confidence: str = "High (deterministic calculation)"
    extraction_reliability: str = "Direct tabular parse (100% complete)"
    judgment_uncertainty: str = "Assumes historical settled transactions"


class InsightModel(BaseModel):
    """Structured insight object with strict separation between facts, reasons, and actions."""
    id: str
    analysis_id: str
    title: str
    category: str  # 'revenue', 'efficiency', 'customer', 'inventory', 'risk'
    plain_english_explanation: str
    priority: str  # 'critical', 'high', 'medium', 'low'

    # STRICT SEPARATION AS MANDATED BY PRD G2
    observed_fact: str          # Strictly calculated mathematical fact
    interpretation: str         # Plausible business rationale
    recommendation: str         # Suggested concrete next action

    # EVIDENCE & TRACEABILITY (PRD G1, FR-4, FR-16)
    evidence: Dict[str, Any]    # Raw computed values, percentages, totals
    method_or_formula: str      # Exact formula used (e.g., "(current_q - prev_q) / prev_q * 100")
    source: SourceReference
    reliability: ReliabilityNote
    assumptions_and_limitations: List[str] = Field(default_factory=list)


class AnalysisModel(BaseModel):
    """Complete analysis snapshot containing verified metrics, chart series, and insights."""
    id: str
    dataset_ids: List[str]
    domain: str  # e.g. 'retail', 'saas', 'logistics', 'general'
    configuration: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, Any] = Field(default_factory=dict)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[InsightModel] = Field(default_factory=list)
