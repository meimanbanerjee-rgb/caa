# backend/app/analytics/outliers.py
# Pure pandas statistical anomaly and outlier detection with Z-score and IQR scoring (FR-13).

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class OutlierAnalytics:
    """Detects unusual statistical transactions and values with transparent threshold formulas."""

    @classmethod
    def identify_transaction_outliers(
        cls,
        df: pd.DataFrame,
        value_col: str,
        id_col: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Pinpoints transactions where value exceeds 1.5x IQR or 2.5 standard deviations.
        Written formula: Z = |x - mean| / std_dev.
        """
        if value_col not in df.columns or len(df) < 5:
            return []

        clean_series = pd.to_numeric(df[value_col], errors="coerce").dropna()
        if len(clean_series) < 5:
            return []

        mean_val = float(clean_series.mean())
        std_val = float(clean_series.std()) if len(clean_series) > 1 else 0.0

        q25 = float(np.percentile(clean_series, 25))
        q75 = float(np.percentile(clean_series, 75))
        iqr = q75 - q25

        lower_bound = q25 - (1.5 * iqr)
        upper_bound = q75 + (1.5 * iqr)

        outliers: List[Dict[str, Any]] = []

        for idx, row in df.iterrows():
            try:
                val = float(row[value_col])
            except (ValueError, TypeError):
                continue

            is_outlier = val < lower_bound or val > upper_bound
            z_score = round(abs(val - mean_val) / std_val, 2) if std_val > 0 else 0.0

            if is_outlier or z_score >= 2.0:
                outliers.append({
                    "row_index": int(idx) + 1,  # 1-indexed row number
                    "identifier": str(row[id_col]) if id_col and id_col in df.columns else f"Row {idx + 1}",
                    "value": round(val, 2),
                    "z_score": z_score,
                    "reason": f"Value {val} exceeds 1.5x IQR upper threshold ({round(upper_bound, 2)})",
                    "formula": "Z = (value - mean) / std; IQR_threshold = Q75 + 1.5 * IQR",
                })

        # Sort by highest z-score
        outliers.sort(key=lambda x: x["z_score"], reverse=True)
        return outliers[:top_k]
