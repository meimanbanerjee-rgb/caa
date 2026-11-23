# backend/app/ingestion/json_parser.py
# Safe JSON and JSONL parser with automatic dictionary flattening and nested record extraction (FR-1, FR-3).

from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import uuid
import pandas as pd
import numpy as np

from backend.app.models.dataset import TableModel, ColumnProfile, ColumnQualityStats


def sanitize_val(v: Any) -> Any:
    """Recursively converts NaN and unhashable/non-serializable values for JSON responses."""
    if isinstance(v, (float, np.floating)) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, dict):
        return {k: sanitize_val(val) for k, val in v.items()}
    if isinstance(v, list):
        return [sanitize_val(item) for item in v]
    return v


class JsonParser:
    """Parses JSON and JSONL documents, extracting tabular records and flattening nested structures."""

    @classmethod
    def parse(
        cls,
        file_path: Path,
        dataset_id: str,
    ) -> Tuple[TableModel, List[str]]:
        """
        Parses JSON or JSONL file into a TableModel.
        Flattens nested keys with dot notation (e.g., customer.id).
        Handles nested arrays and unhashable types safely.
        """
        warnings: List[str] = []
        is_jsonl = file_path.suffix.lower() == ".jsonl"
        records: List[Dict[str, Any]] = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if is_jsonl:
                    for line_num, line in enumerate(f, 1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            record = json.loads(line_str)
                            if isinstance(record, dict):
                                records.append(record)
                            else:
                                warnings.append(f"Line {line_num} in JSONL was not an object and was skipped.")
                        except json.JSONDecodeError as jde:
                            warnings.append(f"Line {line_num} in JSONL could not be decoded: {str(jde)}")
                else:
                    data = json.load(f)
                    if isinstance(data, list):
                        records = [item for item in data if isinstance(item, dict)]
                    elif isinstance(data, dict):
                        found_list = False
                        for key in ["data", "items", "records", "rows", "orders", "results"]:
                            if key in data and isinstance(data[key], list):
                                records = [item for item in data[key] if isinstance(item, dict)]
                                found_list = True
                                break
                        if not found_list:
                            records = [data]
                    else:
                        raise ValueError("JSON content is neither a list nor an object.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON document: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Could not parse JSON file: {str(e)}") from e

        if not records:
            warnings.append(f"JSON file '{file_path.name}' yielded no tabular records.")
            return (
                TableModel(
                    id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    name="JSON Table",
                    row_count=0,
                    column_count=0,
                    columns=[],
                    sample_rows=[],
                ),
                warnings,
            )

        # Normalize nested dictionaries (e.g. customer.id, customer.tier)
        try:
            df = pd.json_normalize(records)
        except Exception:
            df = pd.DataFrame(records)

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Profile columns safely
        columns_profile: List[ColumnProfile] = []
        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            total_count = len(series)
            null_pct = round((null_count / total_count * 100), 1) if total_count > 0 else 0.0

            # Safe distinct count handling unhashable types (lists/dicts)
            try:
                distinct_count = int(series.nunique(dropna=True))
            except TypeError:
                # Convert unhashable elements to string representation for unique counting
                str_series = series.apply(
                    lambda x: json.dumps(x, sort_keys=True) if isinstance(x, (list, dict)) else str(x)
                )
                distinct_count = int(str_series.nunique(dropna=True))

            detected_type = "text"
            if pd.api.types.is_numeric_dtype(series):
                detected_type = "number"
            elif pd.api.types.is_datetime64_any_dtype(series):
                detected_type = "date"
            elif distinct_count < 25 and distinct_count < (total_count * 0.5):
                detected_type = "category"
            elif "id" in col.lower() or "code" in col.lower():
                detected_type = "id"

            stats = ColumnQualityStats(
                null_count=null_count,
                null_percentage=null_pct,
                distinct_count=distinct_count,
                duplicate_count=int(total_count - distinct_count - null_count),
                warnings=[],
            )

            columns_profile.append(
                ColumnProfile(
                    name=col,
                    detected_type=detected_type,
                    suggested_meaning=None,
                    meaning_status="suggested",
                    quality_stats=stats,
                )
            )

        # Sample rows preview with safe serialization
        raw_samples = df.head(15).to_dict(orient="records")
        sample_rows = [sanitize_val(row) for row in raw_samples]

        table = TableModel(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            name="JSON Data",
            row_count=int(len(df)),
            column_count=int(len(df.columns)),
            columns=columns_profile,
            sample_rows=sample_rows,
        )

        return table, warnings
