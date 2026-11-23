# backend/app/analytics/capability_registry.py
# Single source of truth for business analysis capabilities, required roles, and dynamic
# guaranteed-answerable question generation based on confirmed dataset schema mapping.

from typing import Any, Callable, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from backend.app.analytics.schema_mapping import SchemaMapping
from backend.app.analytics.financial_metrics import FinancialMetricsEngine, MissingFieldError


class Capability(BaseModel):
    """Specification of a deterministic analysis capability."""
    id: str
    name: str
    description: str
    required_roles: List[str]
    optional_roles: List[str] = Field(default_factory=list)
    question_templates: List[str] = Field(default_factory=list)


class CapabilityRegistry:
    """Registry managing supported business operations and valid question generation."""

    CAPABILITIES: Dict[str, Capability] = {
        "financial_totals": Capability(
            id="financial_totals",
            name="Total Financials",
            description="Gross sales, discount amounts, net revenue, total costs, profit, and margin %",
            required_roles=["quantity", "unit_price"],
            optional_roles=["discount", "unit_cost"],
            question_templates=[
                "What is our total revenue and gross profit margin?",
                "What are our total sales and total profit?",
                "What is our total discount amount and total cost?",
            ],
        ),
        "product_profit_ranking": Capability(
            id="product_profit_ranking",
            name="Product Profit Ranking",
            description="Ranks products by total profit and margin percentage",
            required_roles=["product", "quantity", "unit_price"],
            optional_roles=["unit_cost", "discount"],
            question_templates=[
                "Which products generate the most profit?",
                "What is our lowest profit product?",
                "Which product has the highest profit margin?",
            ],
        ),
        "product_revenue_ranking": Capability(
            id="product_revenue_ranking",
            name="Product Revenue Ranking",
            description="Ranks products by total net sales",
            required_roles=["product", "quantity", "unit_price"],
            optional_roles=["discount"],
            question_templates=[
                "What are our top products by revenue?",
                "Which product generated the highest net sales?",
            ],
        ),
        "region_comparison": Capability(
            id="region_comparison",
            name="Regional Performance Comparison",
            description="Compares net sales, profit, and margins across geographic regions",
            required_roles=["region", "quantity", "unit_price"],
            optional_roles=["unit_cost", "discount"],
            question_templates=[
                "Which region has the highest revenue?",
                "Compare the performance of different regions.",
            ],
        ),
        "channel_comparison": Capability(
            id="channel_comparison",
            name="Marketing Channel Performance",
            description="Compares revenue, profit, and order volumes across marketing channels",
            required_roles=["marketing_channel", "quantity", "unit_price"],
            optional_roles=["unit_cost", "discount"],
            question_templates=[
                "Which marketing channel performs best?",
                "Compare performance by marketing channel.",
            ],
        ),
        "monthly_trend": Capability(
            id="monthly_trend",
            name="Monthly Revenue & Profit Trend",
            description="Monthly timeline analysis of revenue, margin, and order count",
            required_roles=["date", "quantity", "unit_price"],
            optional_roles=["unit_cost", "discount"],
            question_templates=[
                "Show monthly revenue trend.",
                "Why did revenue decrease last month?",
            ],
        ),
        "customer_ranking": Capability(
            id="customer_ranking",
            name="Customer Rankings",
            description="Ranks top customers by total order volume and net revenue",
            required_roles=["customer", "quantity", "unit_price"],
            optional_roles=["discount"],
            question_templates=[
                "Who are the top 5 customers?",
            ],
        ),
        "average_order_value": Capability(
            id="average_order_value",
            name="Average Order Value (AOV)",
            description="Computes AOV across all transactions or unique order IDs",
            required_roles=["quantity", "unit_price"],
            optional_roles=["order_id", "discount"],
            question_templates=[
                "What is the average order value?",
            ],
        ),
        "data_quality": Capability(
            id="data_quality",
            name="Data Quality Profiling",
            description="Audits missing values, null fields, and duplicate records",
            required_roles=[],
            optional_roles=[],
            question_templates=[
                "How many duplicate rows are there?",
                "Which columns have missing values?",
            ],
        ),
    }

    @classmethod
    def get_supported_capabilities(cls, mapping: SchemaMapping) -> List[Capability]:
        """Identifies all capabilities supported by the dataset columns."""
        supported: List[Capability] = []

        # Check explicit revenue presence as alternative to quantity + unit_price
        has_revenue = mapping.has_role("net_sales") or (
            mapping.has_role("quantity") and mapping.has_role("unit_price")
        )

        for cap in cls.CAPABILITIES.values():
            # If required roles include quantity & unit_price, accept net_sales too
            reqs = list(cap.required_roles)
            if "quantity" in reqs and "unit_price" in reqs and has_revenue:
                reqs.remove("quantity")
                reqs.remove("unit_price")

            if all(mapping.has_role(r) for r in reqs):
                supported.append(cap)

        return supported

    @classmethod
    def generate_suggested_questions(cls, mapping: SchemaMapping, limit: int = 5) -> List[str]:
        """
        Dynamically generates guaranteed-answerable suggested question chips based strictly
        on supported capabilities for the uploaded dataset.
        """
        supported = cls.get_supported_capabilities(mapping)
        suggestions: List[str] = []

        # Priority order for suggested chips
        priority_caps = [
            "financial_totals",
            "product_profit_ranking",
            "region_comparison",
            "channel_comparison",
            "monthly_trend",
            "average_order_value",
            "data_quality",
        ]

        for cap_id in priority_caps:
            cap = next((c for c in supported if c.id == cap_id), None)
            if cap and cap.question_templates:
                suggestions.append(cap.question_templates[0])
                if len(suggestions) >= limit:
                    break

        return suggestions

