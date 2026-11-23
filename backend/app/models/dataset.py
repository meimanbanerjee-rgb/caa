# backend/app/models/dataset.py
# Pydantic schemas for datasets, tables, columns, and transformation logs.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnQualityStats(BaseModel):
    """Data quality statistics for an individual column."""
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    duplicate_count: int = 0
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    outlier_count: int = 0
    warnings: List[str] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    """Metadata, inferred data type, and suggested semantic role of a column."""
    name: str
    detected_type: str  # 'number', 'date', 'text', 'category', 'id'
    suggested_meaning: Optional[str] = None  # e.g. 'revenue', 'order_date', 'customer_id'
    meaning_status: str = "suggested"  # 'suggested' or 'confirmed'
    quality_stats: ColumnQualityStats = Field(default_factory=ColumnQualityStats)


class TableModel(BaseModel):
    """Represents a tabular sheet or section within a file."""
    id: str
    dataset_id: str
    name: str  # Sheet name or default table name
    row_count: int
    column_count: int
    columns: List[ColumnProfile] = Field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)


class TransformationLog(BaseModel):
    """Audit record of data cleaning or transformation applied to a dataset."""
    step: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    column: Optional[str] = None
    action: str
    before: Optional[Any] = None
    after: Optional[Any] = None
    row_reference: Optional[str] = None


class DatasetModel(BaseModel):
    """Master schema for an uploaded business dataset."""
    id: str
    filename: str
    file_type: str  # 'csv', 'tsv', 'xlsx', 'json', 'pdf'
    size_bytes: int
    status: str = "uploaded"  # 'uploaded', 'profiled', 'analyzed', 'error'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tables: List[TableModel] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    transformations: List[TransformationLog] = Field(default_factory=list)
