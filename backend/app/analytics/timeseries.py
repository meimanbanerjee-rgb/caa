# backend/app/analytics/timeseries.py
# Pure pandas time-series analytics, period-over-period growth, and trend trajectories (FR-13).

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class TimeSeriesAnalytics:
    """Computes period-over-period growth and time-series trends without guessing (FR-13, FR-15)."""

    @classmethod
    def compute_periodic_growth(
        cls,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        freq: str = "ME",  # Month End
    ) -> Dict[str, Any]:
        """
        Groups value_col by time periods (monthly) and calculates period-over-period growth.
        Written formula: growth = (current_period - previous_period) / previous_period * 100.
        """
        if date_col not in df.columns or value_col not in df.columns:
            return {"periods": [], "overall_growth_rate": None, "trend_direction": "insufficient_data"}

        clean = df[[date_col, value_col]].copy()
        clean[value_col] = pd.to_numeric(clean[value_col], errors="coerce").fillna(0.0)
        clean["dt"] = pd.to_datetime(clean[date_col], errors="coerce")
        clean = clean.dropna(subset=["dt"]).sort_values(by="dt")

        if len(clean) < 2:
            return {"periods": [], "overall_growth_rate": None, "trend_direction": "insufficient_data"}

        # Resample by month
        clean = clean.set_index("dt")
        try:
            periodic = clean[value_col].resample("ME").sum().reset_index()
        except ValueError:
            # Fallback for pandas versions with legacy 'M' rule
            periodic = clean[value_col].resample("M").sum().reset_index()

        # Remove trailing zero periods outside data bounds
        periodic = periodic[periodic[value_col] > 0]

        periods_data: List[Dict[str, Any]] = []
        prev_val: Optional[float] = None

        for _, row in periodic.iterrows():
            current_val = float(row[value_col])
            period_label = row["dt"].strftime("%Y-%m")
            growth_pct = None

            if prev_val is not None and prev_val > 0:
                growth_pct = round(((current_val - prev_val) / prev_val * 100), 2)

            periods_data.append({
                "period": period_label,
                "value": round(current_val, 2),
                "growth_percentage": growth_pct,
                "formula": "(current - previous) / previous * 100" if growth_pct is not None else "Baseline period",
            })
            prev_val = current_val

        # Overall trend trajectory
        trend_direction = "stable"
        overall_growth = None

        if len(periods_data) >= 2:
            first_val = periods_data[0]["value"]
            last_val = periods_data[-1]["value"]
            if first_val > 0:
                overall_growth = round(((last_val - first_val) / first_val * 100), 2)
                if overall_growth > 5.0:
                    trend_direction = "upward"
                elif overall_growth < -5.0:
                    trend_direction = "downward"

        return {
            "periods": periods_data,
            "overall_growth_rate": overall_growth,
            "trend_direction": trend_direction,
            "written_formula": "growth_rate = ((last_period_revenue - first_period_revenue) / first_period_revenue) * 100",
        }
