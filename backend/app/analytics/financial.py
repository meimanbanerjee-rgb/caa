# backend/app/analytics/financial.py
# Pure pandas financial calculations: margins, profits, AOV, and top/bottom rankings with written formulas (FR-13).

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class FinancialAnalytics:
    """Computes verifiable business financial metrics and performance rankings."""

    @classmethod
    def compute_margins_and_profit(
        cls,
        df: pd.DataFrame,
        revenue_col: str,
        cost_col: Optional[str] = None,
        units_col: Optional[str] = None,
        margin_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates Total Revenue, Total Cost, Gross Profit, and Gross Margin % with written formulas.
        Written formula: Gross Profit = Revenue - Cost; Gross Margin % = (Gross Profit / Revenue) * 100.
        """
        if revenue_col not in df.columns:
            return {}

        rev_series = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0.0)
        total_revenue = float(rev_series.sum())

        total_cost = 0.0
        gross_profit = 0.0
        has_cost_data = False

        if margin_col and margin_col in df.columns:
            margin_series = pd.to_numeric(df[margin_col], errors="coerce").fillna(0.0)
            gross_profit = float(margin_series.sum())
            total_cost = total_revenue - gross_profit
            has_cost_data = True
        elif cost_col and cost_col in df.columns:
            cost_series = pd.to_numeric(df[cost_col], errors="coerce").fillna(0.0)
            if units_col and units_col in df.columns and cost_series.mean() < rev_series.mean() * 0.5:
                # If unit_cost was provided, total cost = unit_cost * units
                u_series = pd.to_numeric(df[units_col], errors="coerce").fillna(1.0)
                total_cost = float((cost_series * u_series).sum())
            else:
                total_cost = float(cost_series.sum())
            gross_profit = total_revenue - total_cost
            has_cost_data = True

        margin_pct = round((gross_profit / total_revenue * 100), 2) if total_revenue > 0 else 0.0

        res: Dict[str, Any] = {
            "total_revenue": round(total_revenue, 2),
            "order_count": int(len(df)),
            "average_order_value": round(total_revenue / len(df), 2) if len(df) > 0 else 0.0,
            "formulas": {
                "total_revenue": f"SUM({revenue_col})",
                "average_order_value": f"SUM({revenue_col}) / COUNT(rows)",
            },
        }

        if has_cost_data:
            res["total_cost"] = round(total_cost, 2)
            res["gross_profit"] = round(gross_profit, 2)
            res["gross_margin_percentage"] = margin_pct
            res["formulas"]["gross_profit"] = f"total_revenue - total_cost"
            res["formulas"]["gross_margin_percentage"] = "(gross_profit / total_revenue) * 100"

        return res

    @classmethod
    def compute_top_and_bottom_performers(
        cls,
        df: pd.DataFrame,
        entity_col: str,
        value_col: str,
        top_n: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ranks top N and bottom N entities (e.g. top products or top customers by revenue).
        """
        if entity_col not in df.columns or value_col not in df.columns:
            return {"top": [], "bottom": []}

        clean = df[[entity_col, value_col]].copy()
        clean[value_col] = pd.to_numeric(clean[value_col], errors="coerce").fillna(0.0)
        clean[entity_col] = clean[entity_col].fillna("Unknown").astype(str)

        grouped = clean.groupby(entity_col)[value_col].sum().reset_index()
        total_val = float(grouped[value_col].sum())

        sorted_desc = grouped.sort_values(by=value_col, ascending=False)
        top_list = []
        for _, row in sorted_desc.head(top_n).iterrows():
            v = float(row[value_col])
            pct = round((v / total_val * 100), 2) if total_val > 0 else 0.0
            top_list.append({
                "name": str(row[entity_col]),
                "value": round(v, 2),
                "share_pct": pct,
            })

        bottom_list = []
        sorted_asc = grouped.sort_values(by=value_col, ascending=True)
        for _, row in sorted_asc.head(top_n).iterrows():
            v = float(row[value_col])
            pct = round((v / total_val * 100), 2) if total_val > 0 else 0.0
            bottom_list.append({
                "name": str(row[entity_col]),
                "value": round(v, 2),
                "share_pct": pct,
            })

        return {"top": top_list, "bottom": bottom_list}
