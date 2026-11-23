# backend/app/analytics/financial_metrics.py
# Pure deterministic Python/pandas financial calculations: Gross/Net sales, discounts,
# costs, profits, group margins (SUM(profit)/SUM(net_sales)*100), rankings, and trends.

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from backend.app.analytics.schema_mapping import SchemaMapping, SchemaMapper


class MissingFieldError(Exception):
    """Raised when an analytical operation lacks required dataset columns."""
    def __init__(self, missing_roles: List[str], message: str) -> None:
        super().__init__(message)
        self.missing_roles = missing_roles
        self.message = message


class FinancialMetricsEngine:
    """Computes exact, verifiable business metrics and group aggregations."""

    @classmethod
    def compute_row_financials(
        cls,
        df: pd.DataFrame,
        mapping: SchemaMapping,
        filters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Derives row-level financial columns:
        - gross_sales = quantity * unit_price (or explicit gross_sales)
        - discount_rate = parsed discount rate [0, 1]
        - discount_amount = gross_sales * discount_rate
        - net_sales = gross_sales - discount_amount
        - total_cost = quantity * unit_cost (or explicit total_cost)
        - profit = net_sales - total_cost
        """
        work_df = df.copy()

        # Apply row-level filters if specified
        if filters:
            for col, val in filters.items():
                if col in work_df.columns and val is not None:
                    if isinstance(val, (int, float)):
                        work_df = work_df[work_df[col] == val]
                    else:
                        work_df = work_df[
                            work_df[col].astype(str).str.strip().str.lower() == str(val).strip().lower()
                        ]

        # 1. Gross Sales
        gross_col = mapping.get_col("gross_sales")
        qty_col = mapping.get_col("quantity")
        price_col = mapping.get_col("unit_price")
        net_col = mapping.get_col("net_sales")

        if gross_col and gross_col in work_df.columns:
            work_df["calc_gross_sales"] = pd.to_numeric(work_df[gross_col], errors="coerce").fillna(0.0)
        elif qty_col and price_col and qty_col in work_df.columns and price_col in work_df.columns:
            q = pd.to_numeric(work_df[qty_col], errors="coerce").fillna(0.0)
            p = pd.to_numeric(work_df[price_col], errors="coerce").fillna(0.0)
            work_df["calc_gross_sales"] = q * p
        elif net_col and net_col in work_df.columns:
            work_df["calc_gross_sales"] = pd.to_numeric(work_df[net_col], errors="coerce").fillna(0.0)
        else:
            raise MissingFieldError(
                missing_roles=["unit_price", "quantity"],
                message="Cannot compute gross sales: neither 'unit_price' & 'quantity' nor explicit 'revenue' column found."
            )

        # 2. Discount Rate & Discount Amount
        disc_col = mapping.get_col("discount")
        if disc_col and disc_col in work_df.columns:
            work_df["calc_discount_rate"] = SchemaMapper.parse_discount_rate(
                work_df[disc_col], mapping.discount_format
            )
            work_df["calc_discount_amount"] = work_df["calc_gross_sales"] * work_df["calc_discount_rate"]
        else:
            work_df["calc_discount_rate"] = 0.0
            work_df["calc_discount_amount"] = 0.0

        # 3. Net Sales
        if net_col and net_col in work_df.columns and not (qty_col and price_col and disc_col):
            # If explicit net sales / revenue column exists without separate components
            work_df["calc_net_sales"] = pd.to_numeric(work_df[net_col], errors="coerce").fillna(0.0)
        else:
            work_df["calc_net_sales"] = work_df["calc_gross_sales"] - work_df["calc_discount_amount"]

        # 4. Total Cost
        cost_col = mapping.get_col("total_cost")
        unit_cost_col = mapping.get_col("unit_cost")

        if unit_cost_col and qty_col and unit_cost_col in work_df.columns and qty_col in work_df.columns:
            q = pd.to_numeric(work_df[qty_col], errors="coerce").fillna(0.0)
            uc = pd.to_numeric(work_df[unit_cost_col], errors="coerce").fillna(0.0)
            work_df["calc_total_cost"] = q * uc
        elif cost_col and cost_col in work_df.columns:
            work_df["calc_total_cost"] = pd.to_numeric(work_df[cost_col], errors="coerce").fillna(0.0)
        else:
            work_df["calc_total_cost"] = 0.0

        # 5. Profit
        work_df["calc_profit"] = work_df["calc_net_sales"] - work_df["calc_total_cost"]

        return work_df

    @classmethod
    def summarize_totals(cls, df_fin: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes business totals: Gross Sales, Discount Amount, Net Sales, Total Cost, Profit, Margin %.
        Group Margin % = SUM(profit) / SUM(net_sales) * 100.
        """
        gross = float(df_fin["calc_gross_sales"].sum())
        discount = float(df_fin["calc_discount_amount"].sum())
        net = float(df_fin["calc_net_sales"].sum())
        cost = float(df_fin["calc_total_cost"].sum())
        profit = float(df_fin["calc_profit"].sum())

        margin_pct = round((profit / net * 100.0), 2) if net > 0 else 0.0

        return {
            "gross_sales": round(gross, 2),
            "discount_amount": round(discount, 2),
            "net_sales": round(net, 2),
            "total_revenue": round(net, 2),  # synonym for net sales
            "total_cost": round(cost, 2),
            "profit": round(profit, 2),
            "gross_profit": round(profit, 2),
            "profit_margin_percentage": margin_pct,
            "gross_margin_percentage": margin_pct,
            "order_count": int(len(df_fin)),
            "average_order_value": round((net / len(df_fin)), 2) if len(df_fin) > 0 else 0.0,
            "formulas": {
                "gross_sales": "SUM(Quantity * Unit_Price)",
                "discount_amount": "SUM(Gross_Sales * Discount_Rate)",
                "net_sales": "Gross_Sales - Discount_Amount",
                "total_cost": "SUM(Quantity * Unit_Cost)",
                "profit": "Net_Sales - Total_Cost",
                "profit_margin_percentage": "(SUM(Profit) / SUM(Net_Sales)) * 100",
                "gross_margin_percentage": "(SUM(Profit) / SUM(Net_Sales)) * 100",
                "average_order_value": "SUM(Net_Sales) / COUNT(rows)",
            },
        }

    @classmethod
    def aggregate_by(
        cls,
        df_fin: pd.DataFrame,
        group_col: str,
    ) -> pd.DataFrame:
        """
        Aggregates financial metrics by group column.
        Margin % = SUM(profit) / SUM(net_sales) * 100 for each group.
        Never averages row-level margins!
        """
        if group_col not in df_fin.columns:
            raise MissingFieldError([group_col], f"Group column '{group_col}' not found in dataset.")

        clean_group = df_fin[group_col].fillna("Unknown").astype(str)
        temp_df = df_fin.copy()
        temp_df["_group"] = clean_group

        agg = temp_df.groupby("_group").agg(
            gross_sales=("calc_gross_sales", "sum"),
            discount_amount=("calc_discount_amount", "sum"),
            net_sales=("calc_net_sales", "sum"),
            total_cost=("calc_total_cost", "sum"),
            profit=("calc_profit", "sum"),
            order_count=("calc_net_sales", "count"),
        ).reset_index()

        total_net = float(agg["net_sales"].sum())
        total_profit = float(agg["profit"].sum())

        # Margin % = SUM(profit) / SUM(net_sales) * 100
        agg["profit_margin_percentage"] = agg.apply(
            lambda r: round((r["profit"] / r["net_sales"] * 100.0), 2) if r["net_sales"] > 0 else 0.0,
            axis=1,
        )

        # Revenue and profit share %
        agg["revenue_share_pct"] = agg["net_sales"].apply(
            lambda v: round((v / total_net * 100.0), 2) if total_net > 0 else 0.0
        )
        agg["profit_share_pct"] = agg["profit"].apply(
            lambda v: round((v / total_profit * 100.0), 2) if total_profit > 0 else 0.0
        )

        agg.rename(columns={"_group": group_col}, inplace=True)
        return agg

    @classmethod
    def rank_entities(
        cls,
        df_agg: pd.DataFrame,
        entity_col: str,
        metric: str = "net_sales",
        ascending: bool = False,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Ranks entities with deterministic tie-breaking:
        1. Metric value (descending or ascending)
        2. Entity name alphabetically (A-Z)
        """
        if entity_col not in df_agg.columns:
            return []

        # Map friendly metric names
        metric_col = metric
        if metric in ["revenue", "sales", "net_revenue"]:
            metric_col = "net_sales"
        elif metric in ["margin", "margin_percentage", "profit_margin"]:
            metric_col = "profit_margin_percentage"
        elif metric in ["gross_profit"]:
            metric_col = "profit"

        if metric_col not in df_agg.columns:
            metric_col = "net_sales"

        sorted_df = df_agg.sort_values(
            by=[metric_col, entity_col],
            ascending=[ascending, True],
        )

        results: List[Dict[str, Any]] = []
        for _, row in sorted_df.head(limit).iterrows():
            item = {
                "name": str(row[entity_col]),
                "metric": metric_col,
                "value": round(float(row[metric_col]), 2),
                "net_sales": round(float(row["net_sales"]), 2),
                "profit": round(float(row["profit"]), 2),
                "profit_margin_percentage": round(float(row["profit_margin_percentage"]), 2),
                "revenue_share_pct": round(float(row.get("revenue_share_pct", 0.0)), 2),
                "order_count": int(row["order_count"]),
            }
            results.append(item)
        return results

    @classmethod
    def compute_monthly_trend(
        cls,
        df_fin: pd.DataFrame,
        date_col: str,
    ) -> List[Dict[str, Any]]:
        """Computes monthly totals, margins, and growth rates."""
        if date_col not in df_fin.columns:
            raise MissingFieldError([date_col], f"Date column '{date_col}' not found.")

        work_df = df_fin.copy()
        work_df["_dt"] = pd.to_datetime(work_df[date_col], errors="coerce")
        work_df = work_df.dropna(subset=["_dt"])
        if work_df.empty:
            return []

        work_df["month"] = work_df["_dt"].dt.strftime("%Y-%m")
        grouped = work_df.groupby("month").agg(
            gross_sales=("calc_gross_sales", "sum"),
            net_sales=("calc_net_sales", "sum"),
            total_cost=("calc_total_cost", "sum"),
            profit=("calc_profit", "sum"),
            orders=("calc_net_sales", "count"),
        ).reset_index().sort_values("month")

        trend: List[Dict[str, Any]] = []
        prev_net: Optional[float] = None

        for _, row in grouped.iterrows():
            net = float(row["net_sales"])
            profit = float(row["profit"])
            margin = round((profit / net * 100.0), 2) if net > 0 else 0.0

            growth_pct = None
            if prev_net is not None and prev_net > 0:
                growth_pct = round(((net - prev_net) / prev_net * 100.0), 2)

            prev_net = net

            trend.append({
                "period": str(row["month"]),
                "value": round(net, 2),
                "net_sales": round(net, 2),
                "profit": round(profit, 2),
                "profit_margin_percentage": margin,
                "order_count": int(row["orders"]),
                "growth_percentage": growth_pct,
            })

        return trend

    @classmethod
    def compute_aov(
        cls,
        df_fin: pd.DataFrame,
        order_id_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates Average Order Value (AOV) and transaction count."""
        total_net = float(df_fin["calc_net_sales"].sum())
        if order_id_col and order_id_col in df_fin.columns:
            order_count = int(df_fin[order_id_col].nunique())
        else:
            order_count = int(len(df_fin))

        aov = round((total_net / order_count), 2) if order_count > 0 else 0.0
        return {
            "average_order_value": aov,
            "total_net_sales": round(total_net, 2),
            "order_count": order_count,
            "formula": "Total Net Sales / Total Orders",
        }
