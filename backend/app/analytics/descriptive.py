# backend/app/analytics/descriptive.py
# Pure pandas deterministic descriptive statistics and category breakdowns (FR-13).

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class DescriptiveAnalytics:
    """Computes exact mathematical descriptive stats and category aggregations."""

    @classmethod
    def compute_summary_stats(cls, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates exact sum, mean, median, std, min, max, q25, q75 for all numeric columns.
        Written formulas: sum = SUM(x), mean = SUM(x)/N, median = sorted_mid(x).
        """
        stats: Dict[str, Dict[str, Any]] = {}
        for col in numeric_cols:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) == 0:
                continue

            n = len(series)
            total = float(series.sum())
            mean = float(series.mean())
            median = float(series.median())
            std_dev = float(series.std()) if n > 1 else 0.0
            min_val = float(series.min())
            max_val = float(series.max())
            q25 = float(np.percentile(series, 25))
            q75 = float(np.percentile(series, 75))

            stats[col] = {
                "count": n,
                "sum": round(total, 2),
                "mean": round(mean, 2),
                "median": round(median, 2),
                "std": round(std_dev, 2),
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "q25": round(q25, 2),
                "q75": round(q75, 2),
                "formula_used": "Pandas standard sample estimators: mean=SUM(x)/N, std=SQRT(VAR)",
            }

        return stats

    @classmethod
    def compute_category_breakdowns(
        cls,
        df: pd.DataFrame,
        category_col: str,
        value_col: str,
        agg_func: str = "sum",
    ) -> List[Dict[str, Any]]:
        """
        Groups df by category_col and aggregates value_col (e.g. revenue by region or category).
        Calculates exact percentage contribution of each category to the total.
        """
        if category_col not in df.columns or value_col not in df.columns:
            return []

        clean_df = df[[category_col, value_col]].copy()
        clean_df[value_col] = pd.to_numeric(clean_df[value_col], errors="coerce").fillna(0.0)
        clean_df[category_col] = clean_df[category_col].fillna("Unknown").astype(str)

        grouped = clean_df.groupby(category_col)[value_col].agg(agg_func).reset_index()
        grouped = grouped.sort_values(by=value_col, ascending=False)

        total_value = float(grouped[value_col].sum())
        breakdowns: List[Dict[str, Any]] = []

        for _, row in grouped.iterrows():
            val = float(row[value_col])
            pct = round((val / total_value * 100), 2) if total_value > 0 else 0.0
            breakdowns.append({
                "category": str(row[category_col]),
                "value": round(val, 2),
                "percentage_of_total": pct,
                "formula": f"SUM({value_col}) / TOTAL({value_col}) * 100",
            })

        return breakdowns
