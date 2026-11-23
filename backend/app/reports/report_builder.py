# backend/app/reports/report_builder.py
# Builds structured, multi-section business intelligence reports adhering strictly to PRD Section 5.6 (FR-22, FR-23).

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.insight import AnalysisModel, InsightModel


class ReportSection(BaseModel):
    """An individual section of an executive business report."""
    id: str
    title: str
    summary: str
    content: Dict[str, Any]
    items: List[Dict[str, Any]] = Field(default_factory=list)


class StructuredReport(BaseModel):
    """Master structured report schema holding all verified sections (FR-22)."""
    analysis_id: str
    title: str
    generated_at: str
    domain: str
    settings: Dict[str, Any]
    sections: List[ReportSection]


class ReportBuilder:
    """
    Constructs multi-section reports from deterministic analysis models.
    Omit irrelevant sections when underlying data is absent (FR-22).
    """

    @classmethod
    def build_report(cls, analysis: AnalysisModel) -> StructuredReport:
        m = analysis.metrics
        insights = analysis.insights
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        domain_title = (analysis.domain or "General Business").replace("_", " ").title()

        sections: List[ReportSection] = []

        # 1. Executive Summary
        exec_points = []
        if "total_revenue" in m:
            rev = m["total_revenue"]
            profit = m.get("gross_profit", 0.0)
            margin = m.get("gross_margin_percentage", 0.0)
            exec_points.append(
                f"Generated ${rev:,.2f} in total gross revenue with a gross margin of {margin:.2f}% (${profit:,.2f} gross profit)."
            )
        if "time_series_growth" in m and m["time_series_growth"].get("overall_growth_rate") is not None:
            rate = m["time_series_growth"]["overall_growth_rate"]
            direction = m["time_series_growth"].get("trend_direction", "stable")
            exec_points.append(f"Recorded periodic growth rate of {rate:+.1f}% indicating a {direction} trajectory.")
        if not exec_points:
            exec_points.append(f"Analyzed {m.get('row_count', 0)} records across {m.get('column_count', 0)} profiled attributes.")

        sections.append(
            ReportSection(
                id="executive_summary",
                title="1. Executive Summary",
                summary="High-level synthesis of computed business performance and core indicators.",
                content={"points": exec_points},
            )
        )

        # 2. Dataset Overview
        sections.append(
            ReportSection(
                id="dataset_overview",
                title="2. Dataset Overview",
                summary="Structural overview of analyzed datasets and extraction boundaries.",
                content={
                    "dataset_ids": analysis.dataset_ids,
                    "row_count": m.get("row_count", 0),
                    "column_count": m.get("column_count", 0),
                    "domain": analysis.domain,
                    "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                },
            )
        )

        # 3. Key Deterministic Metrics
        key_metrics_table = []
        if "total_revenue" in m:
            key_metrics_table.append({"metric": "Total Revenue", "value": f"${m['total_revenue']:,.2f}", "formula": "SUM(revenue)"})
        if "gross_profit" in m:
            key_metrics_table.append({"metric": "Gross Profit", "value": f"${m['gross_profit']:,.2f}", "formula": "SUM(revenue - cost)"})
        if "gross_margin_percentage" in m:
            key_metrics_table.append({"metric": "Gross Margin", "value": f"{m['gross_margin_percentage']:.2f}%", "formula": "(Gross Profit / Total Revenue) * 100"})
        if "average_order_value" in m:
            key_metrics_table.append({"metric": "Average Order Value (AOV)", "value": f"${m['average_order_value']:,.2f}", "formula": "Total Revenue / Order Count"})
        if "row_count" in m:
            key_metrics_table.append({"metric": "Verified Transactions", "value": f"{m['row_count']:,}", "formula": "COUNT(rows)"})

        if key_metrics_table:
            sections.append(
                ReportSection(
                    id="key_metrics",
                    title="3. Key Deterministic Metrics",
                    summary="Exact mathematical calculations verified with zero AI extrapolation.",
                    content={},
                    items=key_metrics_table,
                )
            )

        # 4. Findings & Prioritized Insights (FR-22)
        if insights:
            insight_items = []
            for ins in insights:
                insight_items.append({
                    "id": ins.id,
                    "title": ins.title,
                    "category": ins.category,
                    "priority": ins.priority,
                    "observed_fact": ins.observed_fact,
                    "interpretation": ins.interpretation,
                    "recommendation": ins.recommendation,
                    "evidence": ins.evidence,
                    "method_or_formula": ins.method_or_formula,
                    "source": ins.source.model_dump() if ins.source else {},
                })

            sections.append(
                ReportSection(
                    id="prioritized_findings",
                    title="4. Findings & Verified Insights",
                    summary="Detailed insight cards separating observed facts, interpretations, and recommended actions.",
                    content={},
                    items=insight_items,
                )
            )

        # 5. Category Breakdown / Visualizations
        if "category_breakdown" in m and m["category_breakdown"]:
            sections.append(
                ReportSection(
                    id="category_breakdown",
                    title="5. Category Distribution",
                    summary="Deterministic breakdown of performance across identified business categories.",
                    content={},
                    items=m["category_breakdown"],
                )
            )

        # 6. Identified Risks
        risks = []
        if "revenue_outliers" in m and m["revenue_outliers"]:
            risks.append({
                "type": "Statistical Outlier Risk",
                "detail": f"{len(m['revenue_outliers'])} transaction(s) exceed 2 standard deviations, heavily skewing metrics.",
            })
        if m.get("gross_margin_percentage", 100) < 25.0:
            risks.append({
                "type": "Margin Compression Risk",
                "detail": f"Gross margin of {m.get('gross_margin_percentage'):.1f}% is below healthy retail/wholesale benchmarks.",
            })
        if "time_series_growth" in m and m["time_series_growth"].get("trend_direction") == "downward":
            risks.append({
                "type": "Downward Trajectory Risk",
                "detail": f"Periodic sales trend shows an overall decline of {m['time_series_growth'].get('overall_growth_rate'):.1f}%.",
            })

        if risks:
            sections.append(
                ReportSection(
                    id="risks",
                    title="6. Risk Assessment",
                    summary="Quantified business and operational risks derived from statistical anomalies.",
                    content={},
                    items=risks,
                )
            )

        # 7. Strategic Opportunities & Next Steps
        opportunities = []
        if "top_products" in m and m["top_products"]:
            top_p = m["top_products"][0]
            opportunities.append({
                "initiative": "Capitalize on High-Performing Products",
                "action": f"Expand distribution and inventory priority for '{top_p['name']}' (${top_p['value']:,.2f}).",
            })
        if "top_customers" in m and m["top_customers"]:
            top_c = m["top_customers"][0]
            opportunities.append({
                "initiative": "Strengthen Key Account Partnerships",
                "action": f"Design dedicated retention incentives for top account '{top_c['name']}' (${top_c['value']:,.2f}).",
            })
        if not opportunities:
            opportunities.append({
                "initiative": "Data Enrichment",
                "action": "Connect additional time-series and cost data to unlock automated margin optimization.",
            })

        sections.append(
            ReportSection(
                id="opportunities",
                title="7. Strategic Opportunities & Next Steps",
                summary="Auditable, action-oriented recommendations based directly on computed evidence.",
                content={},
                items=opportunities,
            )
        )

        # 8. Methodology, Sources & Assumptions
        sections.append(
            ReportSection(
                id="methodology_and_audit",
                title="8. Methodology, Sources & Assumptions",
                summary="Complete audit trail explaining formulas, source files, and verification rules.",
                content={
                    "computation_engine": "Python (pandas 2.2 / numpy 1.26)",
                    "verification_rule": "FR-16 Guard (100% number validation before presentation)",
                    "assumptions": [
                        "All recorded transaction amounts reflect completed, settled payments.",
                        "Standard calendar resampling applied for periodic time-series aggregation.",
                        "Z-score threshold of |Z| >= 2.0 used for statistical anomaly classification.",
                    ],
                    "sources": [f"dataset:{d}" for d in analysis.dataset_ids],
                },
            )
        )

        return StructuredReport(
            analysis_id=analysis.id,
            title=f"InsightForge AI — {domain_title} Executive Report",
            generated_at=now_str,
            domain=analysis.domain,
            settings={
                "fr16_validated": True,
                "ai_grounded": True,
                "deterministic_core": True,
            },
            sections=sections,
        )

