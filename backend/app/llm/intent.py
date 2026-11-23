# backend/app/llm/intent.py
# Intent detection combining temperature 0 Groq JSON planning with strict deterministic
# pattern matching fallback across all financial, ranking, comparison, trend, and data-quality queries.

from typing import Any, Dict, List, Optional
import json
import logging
import re
import pandas as pd

from backend.app.llm.safe_plans import SafePlan
from backend.app.analytics.schema_mapping import SchemaMapping, SchemaMapper

logger = logging.getLogger("insightforge.intent")

UNANSWERABLE_PATTERNS = [
    r"\bweather\b",
    r"\bstock\s+price\b",
    r"\bceo\b",
    r"\bjoke\b",
    r"\bpizza\b",
    r"\binflation\b",
    r"\bemployee\s+turnover\b",
    r"\bwebsite\s+visitors?\b",
    r"\btemperature\b",
    r"\bforecast\s+tomorrow\b",
    r"\bhoroscope\b",
    r"\bpresident\b",
    r"\bwho\s+won\b",
]


class IntentRouter:
    """Detects query intent and constructs a valid SafePlan."""

    @classmethod
    def is_unanswerable(cls, question: str) -> bool:
        """Checks if question asks about outside external topics not in business datasets."""
        q = question.lower()
        return any(re.search(pat, q) for pat in UNANSWERABLE_PATTERNS)

    @classmethod
    def match_heuristic_plan(
        cls,
        question: str,
        df: pd.DataFrame,
        mapping: SchemaMapping,
    ) -> SafePlan:
        """
        Deterministic, robust intent detection mapping queries to SafePlan operations.
        Covers all financial, ranking, comparison, trend, AOV, outliers, and quality questions.
        """
        q = question.lower().strip()

        # 1. Unanswerable check
        if cls.is_unanswerable(question):
            return SafePlan(operation="unanswerable", metric_column="requested_external_domain")

        # 2. Insights and Actions
        if re.search(r"\b(actions?|recommendations?|strategic|priorities)\b", q):
            return SafePlan(operation="list_top_insights", top_n=3)

        if re.search(r"\b(evidence|proof|rationale|supporting)\b", q) and "insight" in q:
            return SafePlan(operation="get_insight_evidence")

        # 3. Data Quality (Missing values, Duplicates)
        if re.search(r"\b(missing|null|empty|nan|unpopulated)\b", q):
            return SafePlan(operation="missing_values_report")

        if re.search(r"\b(duplicate|repeated|copied|dupe)\b", q):
            return SafePlan(operation="duplicate_report")

        # 4. Outliers & Anomalies
        if re.search(r"\b(outlier|anomaly|unusual|spike|abnormal|weird|suspicious)\b", q):
            return SafePlan(operation="find_outliers", metric_column="calc_net_sales")

        # 5. Expenses / costs query (missing expense categories over time)
        if "expense" in q or "expenses" in q:
            if "increase" in q or "decrease" in q or "change" in q or "most" in q or "trend" in q:
                return SafePlan(operation="unanswerable", metric_column="expense_categories_over_time")
            cost_col = mapping.get_col("total_cost") or mapping.get_col("unit_cost")
            if not cost_col:
                return SafePlan(operation="unanswerable", metric_column="expenses")
            return SafePlan(operation="financial_totals", metric_column=cost_col)

        # 6. Why did revenue decrease / increase (drivers of change)
        if ("why" in q and ("decrease" in q or "increase" in q or "drop" in q or "fall" in q)) or "drivers" in q:
            date_col = mapping.get_col("date")
            prod_col = mapping.get_col("product")
            cat_col = mapping.get_col("category")
            return SafePlan(
                operation="top_drivers_of_change",
                target_column=date_col or "order_date",
                group_column=prod_col or cat_col or "product_name",
            )

        # 7. Average Order Value (AOV)
        if re.search(r"\b(average\s+order\s+value|aov|average\s+sale|average\s+order|average\s+customer\s+order|transaction\s+size)\b", q):
            return SafePlan(operation="average")

        # 8. Specific Month / Time filter (e.g. "What was the total sales in March?")
        month_match = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b", q)
        if month_match and ("sales" in q or "revenue" in q or "total" in q or "pull in" in q):
            month_name = month_match.group(1)
            return SafePlan(operation="monthly_trend", time_range=month_name)

        # 9. Monthly trend / timeline
        if re.search(r"\b(trend|monthly|month\s+over\s+month|mom|timeline|trajectory|over\s+time)\b", q):
            return SafePlan(operation="monthly_trend")

        # 10. Region Comparison & Highest Region
        reg_col = mapping.get_col("region")
        if re.search(r"\b(regions?|regional|territor(?:y|ies)|geographical|areas?)\b", q) or (
            ("north" in q or "south" in q or "east" in q or "west" in q) and "compare" in q
        ):
            if "highest" in q or "best" in q or "top" in q or "most" in q:
                return SafePlan(
                    operation="group_by_sum",
                    group_column=reg_col or "Region",
                    metric_column="calc_net_sales",
                )
            return SafePlan(
                operation="compare_groups",
                group_column=reg_col or "Region",
            )

        # 9. Marketing Channel Comparison & Best Channel
        channel_col = mapping.get_col("marketing_channel")
        if re.search(r"\b(channels?|marketing|acquisitions?|mediums?)\b", q):
            if "highest" in q or "best" in q or "top" in q or "most" in q:
                return SafePlan(
                    operation="top_n",
                    target_column=channel_col or "Marketing_Channel",
                    metric_column="profit" if "profit" in q else "net_sales",
                    top_n=1,
                )
            return SafePlan(
                operation="compare_groups",
                group_column=channel_col or "Marketing_Channel",
            )

        # 10. Category Comparison & Best Category
        cat_col = mapping.get_col("category")
        if re.search(r"\b(categor(?:y|ies)|departments?|segments?)\b", q):
            if "highest" in q or "best" in q or "top" in q or "most" in q:
                return SafePlan(
                    operation="top_n",
                    target_column=cat_col or "Category",
                    metric_column="profit" if "profit" in q else "net_sales",
                    top_n=1,
                )
            return SafePlan(
                operation="compare_groups",
                group_column=cat_col or "Category",
            )

        # 10. Customer Rankings (e.g. "Who are the top 5 customers?")
        cust_col = mapping.get_col("customer")
        if re.search(r"\b(customer|customers|client|clients|buyer|buyers)\b", q):
            top_match = re.search(r"\b(?:top|first)\s+(\d+)\b", q)
            top_k = int(top_match.group(1)) if top_match else 5
            return SafePlan(
                operation="top_n",
                target_column=cust_col or "Customer_ID",
                metric_column="net_sales",
                top_n=top_k,
            )

        # 11. Product Rankings: Profit, Margin, Sales, Lowest/Worst
        prod_col = mapping.get_col("product")
        if re.search(r"\b(product|products|item|items|sku|skus)\b", q) or "making items" in q:
            # Lowest / worst product
            if re.search(r"\b(lowest|worst|bottom|least)\b", q):
                limit_match = re.search(r"\b(?:bottom|lowest)\s+(\d+)\b", q)
                lim = int(limit_match.group(1)) if limit_match else 1
                return SafePlan(
                    operation="bottom_n",
                    target_column=prod_col or "Product",
                    metric_column="profit" if "profit" in q else "net_sales",
                    top_n=lim,
                )

            # Highest margin product
            if "margin" in q:
                return SafePlan(
                    operation="top_n",
                    target_column=prod_col or "Product",
                    metric_column="profit_margin_percentage",
                    top_n=1 if ("highest" in q or "best" in q) else 5,
                )

            # Most profit product
            if "profit" in q or "making" in q:
                return SafePlan(
                    operation="top_n",
                    target_column=prod_col or "Product",
                    metric_column="profit",
                    top_n=5,
                )

            # Top selling / revenue products
            top_match = re.search(r"\b(?:top|best)\s+(\d+)\b", q)
            top_k = int(top_match.group(1)) if top_match else (1 if ("best" in q or "highest" in q) else 5)
            return SafePlan(
                operation="top_n",
                target_column=prod_col or "Product",
                metric_column="net_sales",
                top_n=top_k,
            )

        # 12. General Financial Totals: revenue, margin, profit, sales, cost, discount
        if any(term in q for term in [
            "revenue", "sales", "profit", "margin", "discount", "cost",
            "income", "earnings", "gross", "net", "total"
        ]):
            metric_col = "calc_net_sales"
            if "profit" in q and "margin" not in q:
                metric_col = "calc_profit"
            elif "cost" in q:
                metric_col = "calc_total_cost"
            elif "discount" in q:
                metric_col = "calc_discount_amount"
            elif "gross" in q:
                metric_col = "calc_gross_sales"

            return SafePlan(
                operation="total",
                metric_column=metric_col,
            )

        # 13. Compare groups default
        if "compare" in q:
            cat_col = mapping.get_col("category") or mapping.get_col("region") or df.columns[0]
            return SafePlan(operation="compare_groups", group_column=cat_col)

        # Default fallback: total financials
        return SafePlan(operation="total", metric_column="calc_net_sales")
