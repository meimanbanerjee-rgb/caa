# backend/tests/unit/test_safe_operations.py
# Unit tests for all 15 deterministic safe pandas operations using hand-verified synthetic sales data.

from pathlib import Path
import pandas as pd
import pytest

from backend.app.llm.safe_plans import (
    op_total,
    op_average,
    op_count,
    op_group_by_sum,
    op_top_n,
    op_bottom_n,
    op_compare_groups,
    op_period_over_period_change,
    op_monthly_trend,
    op_top_drivers_of_change,
    op_find_outliers,
    op_missing_values_report,
    op_duplicate_report,
    op_list_top_insights,
    op_get_insight_evidence,
)
from backend.app.models.insight import InsightModel, SourceReference, ReliabilityNote

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


@pytest.fixture
def sales_df() -> pd.DataFrame:
    csv_path = TEST_DATA_DIR / "clean_sales.csv"
    return pd.read_csv(csv_path)


def test_op_total(sales_df):
    """Hand-verified sum of revenue: 6000+3000+1000+3200+3600+2700+1800+1200+2000+3600 = 28100.00."""
    res = op_total(sales_df, "revenue")
    assert res.status == "success"
    assert res.values["total"] == 28100.00
    assert res.values["count"] == 10


def test_op_average(sales_df):
    """Hand-verified mean of revenue: 28100.00 / 10 = 2810.00."""
    res = op_average(sales_df, "revenue")
    assert res.status == "success"
    assert res.values["average"] == 2810.00


def test_op_count(sales_df):
    """Hand-verified record count: 10 rows and 11 columns."""
    res = op_count(sales_df)
    assert res.status == "success"
    assert res.values["total_rows"] == 10
    assert res.values["total_columns"] == 11


def test_op_group_by_sum_region(sales_df):
    """
    Hand-verified regional revenue:
    North: 6000 + 3200 + 1200 = 10400.00
    West: 3600 + 3600 = 7200.00
    East: 1000 + 2700 + 2000 = 5700.00
    South: 3000 + 1800 = 4800.00
    """
    res = op_group_by_sum(sales_df, "region", "revenue")
    assert res.status == "success"
    assert res.values["highest"]["name"] == "North"
    assert res.values["highest"]["value"] == 10400.00
    breakdown = {b["name"]: b["value"] for b in res.values["breakdown"]}
    assert breakdown["North"] == 10400.00
    assert breakdown["West"] == 7200.00
    assert breakdown["East"] == 5700.00
    assert breakdown["South"] == 4800.00


def test_op_top_n_profit(sales_df):
    """
    Hand-verified profit per product:
    Pro Laptop 15: 2000 + 1200 = 3200.00 (Rank 1)
    Standing Desk: 1500.00 (Rank 2)
    """
    res = op_top_n(sales_df, "product_name", "margin", n=2)
    assert res.status == "success"
    items = res.values["top_n"]
    assert items[0]["name"] == "Pro Laptop 15"
    assert items[0]["value"] == 3200.00
    assert items[1]["name"] == "Standing Desk"
    assert items[1]["value"] == 1500.00


def test_op_bottom_n(sales_df):
    """
    Hand-verified lowest profit product:
    Bookshelf Unit: 480.00 (Lowest)
    """
    res = op_bottom_n(sales_df, "product_name", "margin", n=1)
    assert res.status == "success"
    assert res.values["bottom_n"][0]["name"] == "Bookshelf Unit"
    assert res.values["bottom_n"][0]["value"] == 480.00


def test_op_compare_groups(sales_df):
    """Compares metrics (revenue, margin) across regions."""
    res = op_compare_groups(sales_df, "region", ["revenue", "margin"])
    assert res.status == "success"
    groups = {g["region"]: g for g in res.values["groups"]}
    assert groups["North"]["revenue"] == 10400.00
    assert groups["North"]["margin"] == 3680.00


def test_op_monthly_trend_and_filter(sales_df):
    """
    Hand-verified monthly revenue:
    2026-01: 6000 + 3000 + 1000 = 10000.00
    2026-02: 3200 + 3600 + 2700 = 9500.00
    2026-03: 1800 + 1200 + 2000 + 3600 = 8600.00
    """
    res = op_monthly_trend(sales_df, "order_date", "revenue")
    assert res.status == "success"
    periods = {p["period"]: p["value"] for p in res.values["periods"]}
    assert periods["2026-01"] == 10000.00
    assert periods["2026-02"] == 9500.00
    assert periods["2026-03"] == 8600.00

    # Test filtering specific month March
    res_march = op_monthly_trend(sales_df, "order_date", "revenue", month_filter="March")
    assert res_march.values["filtered_month"]["value"] == 8600.00


def test_op_period_over_period_change(sales_df):
    """
    Hand-verified change from Feb ($9,500) to Mar ($8,600):
    Diff = -$900.00, Pct = -9.47%.
    """
    res = op_period_over_period_change(sales_df, "order_date", "revenue")
    assert res.status == "success"
    recent = res.values["recent_change"]
    assert recent["from_period"] == "2026-02"
    assert recent["to_period"] == "2026-03"
    assert recent["absolute_change"] == -900.00
    assert recent["percentage_change"] == -9.47


def test_op_top_drivers_of_change(sales_df):
    """Diagnoses which products drove the Feb to Mar decrease."""
    res = op_top_drivers_of_change(sales_df, "order_date", "product_name", "revenue")
    assert res.status == "success"
    assert res.values["from_period"] == "2026-02"
    assert res.values["to_period"] == "2026-03"
    assert res.values["biggest_drag"] is not None


def test_op_find_outliers(sales_df):
    """Identifies outlier transaction ORD-1001 with revenue 6000.00."""
    res = op_find_outliers(sales_df, "revenue", id_col="order_id", z_thresh=1.8)
    assert res.status == "success"
    assert res.values["outliers_found"] >= 1
    assert any(o["value"] == 6000.00 for o in res.values["outliers"])


def test_op_missing_values_report(sales_df):
    """Hand-verified: clean_sales.csv has 0 null values across all columns."""
    res = op_missing_values_report(sales_df)
    assert res.status == "success"
    assert res.values["all_columns_clean"] is True
    assert len(res.values["columns_with_missing"]) == 0


def test_op_duplicate_report(sales_df):
    """Hand-verified: clean_sales.csv has 0 duplicate rows."""
    res = op_duplicate_report(sales_df)
    assert res.status == "success"
    assert res.values["duplicate_count"] == 0
    assert res.values["is_clean"] is True


def test_op_list_top_insights_and_evidence():
    """Verifies listing top recommendations and extracting mathematical evidence."""
    mock_insight = InsightModel(
        id="ins-1",
        analysis_id="an-1",
        title="Revenue Concentration",
        category="revenue",
        plain_english_explanation="High revenue concentration in North.",
        priority="critical",
        observed_fact="North region accounts for $10,400.00 of total revenue.",
        interpretation="Strong enterprise market in North.",
        recommendation="Expand enterprise sales reps in North.",
        evidence={"north_revenue": 10400.00, "percentage": 37.01},
        method_or_formula="sum(revenue where region == 'North')",
        source=SourceReference(filename="clean_sales.csv", sheet="Sheet1", row_range="1-10"),
        reliability=ReliabilityNote(),
    )

    # 1. List top insights
    res_list = op_list_top_insights([mock_insight], n=1)
    assert res_list.status == "success"
    assert len(res_list.values["top_actions"]) == 1
    assert "Expand enterprise" in res_list.values["top_actions"][0]["recommendation"]

    # 2. Get insight evidence
    res_ev = op_get_insight_evidence([mock_insight], insight_id="ins-1")
    assert res_ev.status == "success"
    assert res_ev.values["formula"] == "sum(revenue where region == 'North')"
    assert res_ev.values["evidence"]["north_revenue"] == 10400.00

