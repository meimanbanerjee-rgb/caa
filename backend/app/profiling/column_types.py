# backend/app/profiling/column_types.py
# In-depth column type detection: numbers, dates, categories, IDs, and text (FR-7).

from typing import Any, List, Tuple
import re
import pandas as pd
import numpy as np


class ColumnTypeDetector:
    """Detects statistical and semantic data types for tabular columns."""

    ID_KEYWORDS = {"id", "uuid", "key", "code", "pk", "fk", "num", "no", "identifier", "sku"}

    @classmethod
    def detect_type(cls, series: pd.Series, column_name: str) -> str:
        """
        Infers whether column represents 'number', 'date', 'category', 'id', or 'text'.
        Checks column name heuristics, cardinality ratios, and parseable patterns.
        """
        col_lower = column_name.lower().strip()
        non_null_series = series.dropna()

        if len(non_null_series) == 0:
            return "text"

        # 1. ID detection heuristic
        # If column name ends with _id, id, or matches ID keywords and values are high-cardinality
        tokens = set(re.split(r"[_\s\.-]", col_lower))
        if tokens.intersection(cls.ID_KEYWORDS) or col_lower.endswith("id"):
            distinct_ratio = non_null_series.nunique() / len(non_null_series)
            if distinct_ratio > 0.4:
                return "id"

        # 2. Date detection
        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"

        if "date" in col_lower or "time" in col_lower or "timestamp" in col_lower:
            # Test sample parsing
            sample = non_null_series.head(20).astype(str)
            try:
                converted = pd.to_datetime(sample, errors="coerce")
                if converted.notna().sum() >= len(sample) * 0.7:
                    return "date"
            except Exception:
                pass

        # 3. Numeric detection
        if pd.api.types.is_numeric_dtype(series):
            return "number"

        # Check if text column is actually formatted numbers (e.g. "$1,200.50", "45%")
        sample_str = non_null_series.head(30).astype(str)
        cleaned_num = sample_str.str.replace(r"[\$,€£%\s,]", "", regex=True)
        numeric_count = pd.to_numeric(cleaned_num, errors="coerce").notna().sum()
        if numeric_count >= len(sample_str) * 0.8:
            return "number"

        # 4. Category detection (low distinct count relative to total rows)
        distinct_count = non_null_series.nunique()
        total_count = len(non_null_series)
        if (distinct_count <= 25 and distinct_count <= total_count * 0.3) or distinct_count <= 5:
            return "category"

        # 5. Fallback to generic text
        return "text"
