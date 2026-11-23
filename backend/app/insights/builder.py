# backend/app/insights/builder.py
# Transforms deterministic analytics results into structured, auditable insight objects (FR-16).

from typing import Any, Dict, List
import uuid

from backend.app.models.dataset import DatasetModel
from backend.app.models.insight import InsightModel, SourceReference, ReliabilityNote
from backend.app.insights.priority import InsightPriorityScorer
from backend.app.insights.validator import InsightValidator


class InsightBuilder:
    """Builds and validates structured insight objects adhering strictly to PRD Section 5.4."""

    @classmethod
    def build_insights(
        cls,
        analysis_id: str,
        dataset: DatasetModel,
        metrics: Dict[str, Any],
    ) -> List[InsightModel]:
        """
        Synthesizes structured insight cards with separate Fact, Interpretation, and Action.
        Validates every number against computed metrics before inclusion (FR-16).
        """
        raw_insights: List[InsightModel] = []
        filename = dataset.filename
        row_count = metrics.get("row_count", 0)

        # 1. Financial Performance Insight (Revenue, Gross Margin, AOV)
        if "total_revenue" in metrics:
            rev = metrics["total_revenue"]
            profit = metrics.get("gross_profit", 0.0)
            margin_pct = metrics.get("gross_margin_percentage", 0.0)
            aov = metrics.get("average_order_value", 0.0)

            fact = (
                f"Total revenue is ${rev:,.2f} across {row_count} transactions with an "
                f"Average Order Value (AOV) of ${aov:,.2f}."
            )
            if "gross_margin_percentage" in metrics:
                fact += f" Gross profit is ${profit:,.2f} yielding a {margin_pct}% gross margin."

            evidence_data = {
                "total_revenue": rev,
                "gross_profit": profit,
                "gross_margin_percentage": margin_pct,
                "average_order_value": aov,
                "row_count": row_count,
            }

            prio = InsightPriorityScorer.calculate_priority(
                category="revenue",
                evidence=evidence_data,
            )

            raw_insights.append(
                InsightModel(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    title="Revenue & Profitability Performance",
                    category="revenue",
                    plain_english_explanation=f"Business generated ${rev:,.2f} in total gross sales with healthy profitability margins.",
                    priority=prio,
                    observed_fact=fact,
                    interpretation="Strong sales velocity across primary product tiers indicates consistent customer conversion.",
                    recommendation="Focus marketing spend on products exceeding the 40% margin threshold.",
                    evidence=evidence_data,
                    method_or_formula="margin_pct = (revenue - cost) / revenue * 100; aov = revenue / orders",
                    source=SourceReference(
                        filename=filename,
                        sheet="Main Table",
                        row_range=f"Rows 1 to {row_count}",
                    ),
                    reliability=ReliabilityNote(
                        statistical_confidence=f"High (N={row_count} verified records)",
                        extraction_reliability="Direct tabular calculation (100% complete)",
                        judgment_uncertainty="Assumes recorded costs reflect final settled invoices",
                    ),
                    assumptions_and_limitations=["Data reflects historical completed transactions only."],
                )
            )

        # 2. Category Concentration Insight
        if "category_breakdown" in metrics and metrics["category_breakdown"]:
            top_cat = metrics["category_breakdown"][0]
            cat_name = top_cat["category"]
            cat_val = top_cat["value"]
            cat_pct = top_cat.get("percentage_of_total", top_cat.get("percentage", 0.0))

            evidence_data = {
                "category": cat_name,
                "value": cat_val,
                "percentage_of_total": cat_pct,
            }

            prio = InsightPriorityScorer.calculate_priority(
                category="efficiency",
                evidence=evidence_data,
            )

            raw_insights.append(
                InsightModel(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    title=f"Category Concentration in {cat_name}",
                    category="efficiency",
                    plain_english_explanation=f"The '{cat_name}' category represents {cat_pct}% of total sales.",
                    priority=prio,
                    observed_fact=f"'{cat_name}' generated ${cat_val:,.2f}, representing {cat_pct}% of total revenue.",
                    interpretation="High revenue concentration in a single category presents both a core strength and potential diversification risk.",
                    recommendation=f"Maintain stock availability for {cat_name} while expanding secondary lines.",
                    evidence=evidence_data,
                    method_or_formula="share = SUM(category_revenue) / TOTAL(revenue) * 100",
                    source=SourceReference(
                        filename=filename,
                        sheet="Main Table",
                        row_range="All records",
                    ),
                    reliability=ReliabilityNote(
                        statistical_confidence="High (deterministic groupby sum)",
                        extraction_reliability="100% categoric match",
                        judgment_uncertainty="Seasonality or promotions may influence concentration",
                    ),
                    assumptions_and_limitations=[],
                )
            )

        # 3. Time-Series Trend & Momentum Insight
        if "time_series_growth" in metrics and metrics["time_series_growth"]["periods"]:
            ts = metrics["time_series_growth"]
            rate = ts.get("overall_growth_rate")
            direction = ts.get("trend_direction", "stable")
            periods = ts["periods"]

            if rate is not None and len(periods) >= 2:
                first_val = periods[0].get("value", periods[0].get("net_sales", 0.0))
                last_val = periods[-1].get("value", periods[-1].get("net_sales", 0.0))

                evidence_data = {
                    "first_period_value": first_val,
                    "last_period_value": last_val,
                    "growth_percentage": rate,
                    "period_count": len(periods),
                }

                prio = InsightPriorityScorer.calculate_priority(
                    category="revenue",
                    evidence=evidence_data,
                    is_negative_trend=(direction == "downward"),
                )

                raw_insights.append(
                    InsightModel(
                        id=str(uuid.uuid4()),
                        analysis_id=analysis_id,
                        title=f"Revenue Trajectory: {direction.title()} Trend ({rate:+0.1f}%)",
                        category="revenue",
                        plain_english_explanation=f"Revenue evolved by {rate:+0.1f}% from the initial observed period to the latest period.",
                        priority=prio,
                        observed_fact=f"Periodic revenue moved from ${first_val:,.2f} to ${last_val:,.2f} ({rate:+0.1f}% growth).",
                        interpretation=f"Business exhibits an {direction} sales trajectory over the analyzed timeline.",
                        recommendation="Review monthly channel attribution to capitalize on compounding momentum.",
                        evidence=evidence_data,
                        method_or_formula="growth = (last_period - first_period) / first_period * 100",
                        source=SourceReference(
                            filename=filename,
                            sheet="Main Table",
                            row_range=f"Timeline spanning {len(periods)} periods",
                        ),
                        reliability=ReliabilityNote(
                            statistical_confidence=f"Moderate (N={len(periods)} periods recorded)",
                            extraction_reliability="Monthly resampled aggregations",
                            judgment_uncertainty="Requires multi-year baseline to isolate seasonal effects",
                        ),
                        assumptions_and_limitations=["Assumes monthly dates represent invoice completion dates."],
                    )
                )

        # 4. Outlier Transaction Warning Insight
        if "revenue_outliers" in metrics and metrics["revenue_outliers"]:
            top_outlier = metrics["revenue_outliers"][0]
            val = top_outlier["value"]
            z = top_outlier["z_score"]
            row_idx = top_outlier["row_index"]
            ident = top_outlier["identifier"]

            evidence_data = {
                "outlier_value": val,
                "z_score": z,
                "row_index": row_idx,
            }

            prio = InsightPriorityScorer.calculate_priority(
                category="risk",
                evidence=evidence_data,
            )

            raw_insights.append(
                InsightModel(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    title=f"Statistical Anomaly Detected (Z-Score: {z})",
                    category="risk",
                    plain_english_explanation=f"Transaction at row {row_idx} ({ident}) of ${val:,.2f} is a significant statistical outlier.",
                    priority=prio,
                    observed_fact=f"Transaction for '{ident}' at row {row_idx} recorded ${val:,.2f} with a statistical Z-Score of {z}.",
                    interpretation="Large outlier transactions significantly skew averages and require separate audit scrutiny.",
                    recommendation="Review contract terms and fulfillment timeline for this high-value outlier.",
                    evidence=evidence_data,
                    method_or_formula="Z = |value - mean| / std_dev",
                    source=SourceReference(
                        filename=filename,
                        sheet="Main Table",
                        row_range=f"Row {row_idx}",
                    ),
                    reliability=ReliabilityNote(
                        statistical_confidence="High (Parametric standard deviation check)",
                        extraction_reliability="Exact row index mapping",
                        judgment_uncertainty="Does not differentiate between error vs genuine enterprise order",
                    ),
                    assumptions_and_limitations=["Assumes roughly bell-curve distribution for Z-score thresholding."],
                )
            )

        # 5. FR-16 Guard: Filter and validate all insights
        validated_insights: List[InsightModel] = []
        for ins in raw_insights:
            is_valid, unverified = InsightValidator.validate_insight(
                observed_fact=ins.observed_fact,
                evidence=ins.evidence,
                all_metrics=metrics,
            )
            if is_valid:
                validated_insights.append(ins)
            else:
                # FR-16: Block insight if numbers fail validation
                print(f"[FR-16 Guard Blocked] Insight '{ins.title}' had unverified numbers: {unverified}")

        return validated_insights
