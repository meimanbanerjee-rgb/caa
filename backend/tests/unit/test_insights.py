# backend/tests/unit/test_insights.py
# Unit tests for Insight Priority Scoring, FR-16 Number Validation Guard, and Insight Building.

import pytest
from backend.app.insights.priority import InsightPriorityScorer
from backend.app.insights.validator import InsightValidator
from backend.app.insights.builder import InsightBuilder
from backend.app.models.dataset import DatasetModel


def test_priority_scorer_critical_tier():
    """Verify high category concentration (>50%) or severe negative trend scores critical/high."""
    prio_critical = InsightPriorityScorer.calculate_priority(
        category="efficiency",
        evidence={"percentage_of_total": 62.28},
    )
    assert prio_critical in ["critical", "high"]

    prio_urgent = InsightPriorityScorer.calculate_priority(
        category="revenue",
        evidence={"growth_percentage": -15.0},
        is_negative_trend=True,
    )
    assert prio_urgent in ["critical", "high"]


def test_priority_scorer_low_tier():
    """Verify minor metrics with low category weight score as low/medium."""
    prio_low = InsightPriorityScorer.calculate_priority(
        category="metadata",
        evidence={"share_pct": 5.0},
    )
    assert prio_low in ["medium", "low"]


def test_insight_validator_passes_verified_numbers():
    """Verify FR-16: Exactly matching computed numbers pass validation."""
    computed_evidence = {
        "total_revenue": 28100.00,
        "gross_profit": 11430.00,
        "gross_margin_percentage": 40.68,
        "order_count": 10,
    }
    fact_text = "Total revenue is $28,100.00 across 10 transactions with 40.68% margin and $11,430.00 profit."

    is_valid, unverified = InsightValidator.validate_insight(
        observed_fact=fact_text,
        evidence=computed_evidence,
        all_metrics=computed_evidence,
    )

    assert is_valid is True
    assert len(unverified) == 0


def test_insight_validator_blocks_hallucinated_numbers():
    """Verify FR-16: Fabricated or uncalculated numbers fail validation and are blocked."""
    computed_evidence = {
        "total_revenue": 28100.00,
        "gross_profit": 11430.00,
    }
    # Notice $999,999.00 and 85.5% are completely made up (simulating AI hallucination)
    hallucinated_fact = "Total revenue reached $999,999.00 with a record 85.5% margin."

    is_valid, unverified = InsightValidator.validate_insight(
        observed_fact=hallucinated_fact,
        evidence=computed_evidence,
        all_metrics=computed_evidence,
    )

    assert is_valid is False
    assert 999999.0 in unverified or 85.5 in unverified


def test_insight_builder_generates_and_validates():
    """Verify InsightBuilder produces valid InsightModel objects with source and formula."""
    dataset = DatasetModel(
        id="ds_test_123",
        filename="sales_q1.csv",
        file_type="csv",
        size_bytes=2048,
        status="profiled",
        tables=[],
        warnings=[],
    )

    metrics = {
        "row_count": 10,
        "total_revenue": 28100.00,
        "gross_profit": 11430.00,
        "gross_margin_percentage": 40.68,
        "average_order_value": 2810.00,
        "category_breakdown": [
            {"category": "Electronics", "value": 17500.00, "percentage_of_total": 62.28}
        ],
        "time_series_growth": {
            "overall_growth_rate": -14.0,
            "trend_direction": "downward",
            "periods": [
                {"period": "2026-01", "value": 10000.00},
                {"period": "2026-03", "value": 8600.00},
            ],
        },
    }

    insights = InsightBuilder.build_insights("analysis_test_123", dataset, metrics)
    assert len(insights) >= 2

    for ins in insights:
        # Check PRD fields
        assert ins.observed_fact != ""
        assert ins.interpretation != ""
        assert ins.recommendation != ""
        assert ins.method_or_formula != ""
        assert ins.source.filename == "sales_q1.csv"
        assert ins.priority in ["critical", "high", "medium", "low"]
        # Double check FR-16 compliance
        is_valid, _ = InsightValidator.validate_insight(ins.observed_fact, ins.evidence, metrics)
        assert is_valid is True
