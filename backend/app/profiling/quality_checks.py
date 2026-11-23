# backend/app/profiling/quality_checks.py
# Data quality profiler detecting missing values, duplicates, mixed date formats, invalid numbers, outliers, and inconsistent labels (FR-9).

from typing import Any, Dict, List, Tuple
import re
import pandas as pd
import numpy as np

from backend.app.models.dataset import ColumnQualityStats, TransformationLog


# Common US State abbreviation / full name map for inconsistent label detection
STATE_SYNONYMS = {
    "ny": "new york",
    "ca": "california",
    "tx": "texas",
    "fl": "florida",
    "il": "illinois",
    "pa": "pennsylvania",
    "oh": "ohio",
    "ga": "georgia",
    "nc": "north carolina",
    "mi": "michigan",
}


class QualityProfiler:
    """Profiles tabular data quality and flags inconsistencies without modifying original data."""

    @classmethod
    def check_mixed_dates(cls, series: pd.Series) -> Tuple[bool, List[str]]:
        """Detects whether date column contains mixed formatting styles (e.g. YYYY-MM-DD vs MM/DD/YYYY)."""
        clean_str = series.dropna().astype(str).str.strip()
        if len(clean_str) < 2:
            return False, []

        has_iso = clean_str.str.contains(r"^\d{4}-\d{1,2}-\d{1,2}", regex=True).any()
        has_slash = clean_str.str.contains(r"^\d{1,2}/\d{1,2}/\d{2,4}", regex=True).any()

        if has_iso and has_slash:
            return True, ["Mixed date formats detected (ISO YYYY-MM-DD mixed with slash MM/DD/YYYY)."]
        return False, []

    @classmethod
    def check_inconsistent_labels(cls, series: pd.Series) -> List[str]:
        """Detects abbreviated vs full label conflicts (e.g., 'NY' vs 'New York')."""
        warnings = []
        clean_vals = series.dropna().astype(str).str.strip().str.lower().unique()
        val_set = set(clean_vals)

        for abbr, full in STATE_SYNONYMS.items():
            if abbr in val_set and full in val_set:
                warnings.append(f"Inconsistent category labels found: '{abbr.upper()}' and '{full.title()}' both exist.")

        return warnings

    @classmethod
    def check_invalid_numbers(cls, series: pd.Series) -> Tuple[int, List[str]]:
        """Detects non-numeric tokens inside numeric or currency columns."""
        clean_s = series.dropna().astype(str).str.strip()
        invalid_count = 0
        for val in clean_s:
            v_clean = re.sub(r"[\$,€£%,\s]", "", val)
            try:
                float(v_clean)
            except ValueError:
                invalid_count += 1

        if invalid_count > 0:
            return invalid_count, [f"{invalid_count} cell(s) contain unparseable numeric values."]
        return 0, []

    @classmethod
    def detect_outliers(cls, series: pd.Series) -> Tuple[int, float, float]:
        """
        Detects statistical outliers using Interquartile Range (IQR).
        Returns: (outlier_count, lower_bound, upper_bound)
        """
        numeric_series = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric_series) < 5:
            return 0, 0.0, 0.0

        q25 = float(np.percentile(numeric_series, 25))
        q75 = float(np.percentile(numeric_series, 75))
        iqr = q75 - q25

        if iqr == 0:
            return 0, q25, q75

        lower_bound = q25 - (1.5 * iqr)
        upper_bound = q75 + (1.5 * iqr)

        outlier_mask = (numeric_series < lower_bound) | (numeric_series > upper_bound)
        outlier_count = int(outlier_mask.sum())

        return outlier_count, round(lower_bound, 2), round(upper_bound, 2)

    @classmethod
    def profile_column(
        cls,
        series: pd.Series,
        column_name: str,
        detected_type: str,
    ) -> ColumnQualityStats:
        """Runs complete quality check battery on a single column."""
        total_count = len(series)
        null_count = int(series.isna().sum())
        null_pct = round((null_count / total_count * 100), 2) if total_count > 0 else 0.0
        distinct_count = int(series.nunique(dropna=True))
        duplicate_count = max(0, total_count - distinct_count - null_count)

        warnings: List[str] = []
        min_val = None
        max_val = None
        mean_val = None
        outlier_count = 0

        # Number-specific checks
        if detected_type == "number":
            num_series = pd.to_numeric(series, errors="coerce")
            valid_nums = num_series.dropna()
            if len(valid_nums) > 0:
                min_val = float(valid_nums.min())
                max_val = float(valid_nums.max())
                mean_val = round(float(valid_nums.mean()), 2)
                outlier_count, _, _ = cls.detect_outliers(valid_nums)
                if outlier_count > 0:
                    warnings.append(f"{outlier_count} statistical outlier(s) detected via 1.5x IQR rule.")

            invalids, inv_warn = cls.check_invalid_numbers(series)
            warnings.extend(inv_warn)

        # Date-specific checks
        elif detected_type == "date":
            is_mixed, date_warn = cls.check_mixed_dates(series)
            warnings.extend(date_warn)

        # Category/Text-specific checks
        elif detected_type in ["category", "text"]:
            label_warn = cls.check_inconsistent_labels(series)
            warnings.extend(label_warn)

        if null_count > 0:
            warnings.append(f"{null_count} missing value(s) ({null_pct}%).")

        return ColumnQualityStats(
            null_count=null_count,
            null_percentage=null_pct,
            distinct_count=distinct_count,
            duplicate_count=duplicate_count,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            outlier_count=outlier_count,
            warnings=warnings,
        )
