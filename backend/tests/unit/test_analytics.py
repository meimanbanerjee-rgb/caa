# backend/tests/unit/test_analytics.py
# Unit tests verifying that deterministic calculations match hand-calculated values exactly (FR-13).

from pathlib import Path
import pandas as pd
import pytest

from backend.app.profiling.semantic_fields import SemanticFieldInferrer
from backend.app.profiling.column_types import ColumnTypeDetector
from backend.app.profiling.quality_checks import QualityProfiler
from backend.app.analytics.financial import FinancialAnalytics
from backend.app.analytics.descriptive import DescriptiveAnalytics
from backend.app.analytics.timeseries import TimeSeriesAnalytics
from backend.app.analytics.outliers import OutlierAnalytics

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def test_hand_calculated_metrics_on_clean_sales():
    """
    CRITICAL PRD ACCEPTANCE CHECK:
    Verify that Python (pandas) calculations match hand-calculated ground truth:
    - Total Revenue = $28,100.00
    - Total Cost = $16,670.00
    - Gross Profit = $11,430.00
    - Gross Margin % = 40.68%
    - Average Order Value = $2,810.00
    """
    df = pd.read_csv(TEST_DATA_DIR / "clean_sales.csv")

    financial = FinancialAnalytics.compute_margins_and_profit(
        df=df,
        revenue_col="revenue",
        cost_col="unit_cost",
        units_col="units_sold",
        margin_col="margin",
    )

    # 1. Total Revenue: 6000 + 3000 + 1000 + 3200 + 3600 + 2700 + 1800 + 1200 + 2000 + 3600 = 28100.0
    assert financial["total_revenue"] == 28100.00

    # 2. Total Cost: 16670.00
    assert financial["total_cost"] == 16670.00

    # 3. Gross Profit: 28100 - 16670 = 11430.00
    assert financial["gross_profit"] == 11430.00

    # 4. Gross Margin %: 11430 / 28100 * 100 = 40.68%
    assert financial["gross_margin_percentage"] == 40.68

    # 5. Average Order Value (AOV): 28100 / 10 = 2810.00
    assert financial["average_order_value"] == 2810.00


def test_category_breakdown_matches_hand_calculation():
    """
    Verify category revenue breakdown:
    - Electronics: 6000 + 3200 + 2700 + 2000 + 3600 = $17,500.00 (62.28%)
    - Furniture: 3000 + 3600 + 1200 = $7,800.00 (27.76%)
    - Office Supplies: 1000 + 1800 = $2,800.00 (9.96%)
    """
    df = pd.read_csv(TEST_DATA_DIR / "clean_sales.csv")
    breakdown = DescriptiveAnalytics.compute_category_breakdowns(df, "category", "revenue")

    elec = next(b for b in breakdown if b["category"] == "Electronics")
    assert elec["value"] == 17500.00
    assert elec["percentage_of_total"] == 62.28

    furn = next(b for b in breakdown if b["category"] == "Furniture")
    assert furn["value"] == 7800.00
    assert furn["percentage_of_total"] == 27.76

    supp = next(b for b in breakdown if b["category"] == "Office Supplies")
    assert supp["value"] == 2800.00
    assert supp["percentage_of_total"] == 9.96


def test_top_performers_ranking_matches_hand_calculation():
    """
    Verify product ranking:
    - Top 1 Product: 'Pro Laptop 15' = 6000 + 3600 = $9,600.00 (34.16%)
    - Top 1 Customer: 'CUST-201' = 6000 + 3200 = $9,200.00 (32.74%)
    """
    df = pd.read_csv(TEST_DATA_DIR / "clean_sales.csv")
    prod_rank = FinancialAnalytics.compute_top_and_bottom_performers(df, "product_name", "revenue", top_n=1)
    assert prod_rank["top"][0]["name"] == "Pro Laptop 15"
    assert prod_rank["top"][0]["value"] == 9600.00
    assert prod_rank["top"][0]["share_pct"] == 34.16

    cust_rank = FinancialAnalytics.compute_top_and_bottom_performers(df, "customer_id", "revenue", top_n=1)
    assert cust_rank["top"][0]["name"] == "CUST-201"
    assert cust_rank["top"][0]["value"] == 9200.00


def test_quality_checks_detect_mixed_dates_and_inconsistent_labels():
    """Verify FR-9: detect mixed date formats, invalid numbers, and inconsistent state labels."""
    df = pd.read_csv(TEST_DATA_DIR / "messy_data.csv")

    # 1. Mixed date format detection
    is_mixed, date_warn = QualityProfiler.check_mixed_dates(df["order_date"])
    assert is_mixed is True
    assert len(date_warn) > 0

    # 2. Inconsistent category labels ('NY' vs 'New York')
    label_warn = QualityProfiler.check_inconsistent_labels(df["state"])
    assert len(label_warn) > 0
    assert any("NY" in w and "New York" in w for w in label_warn)

    # 3. Invalid numbers in unit_price ('not-a-number')
    inv_count, inv_warn = QualityProfiler.check_invalid_numbers(df["unit_price"])
    assert inv_count >= 1
    assert len(inv_warn) > 0


def test_semantic_field_inferrer():
    """Verify FR-8: automatically identifies revenue, customer_id, order_date, margin."""
    assert SemanticFieldInferrer.infer_meaning("revenue", "number") == "revenue"
    assert SemanticFieldInferrer.infer_meaning("total_amount", "number") == "revenue"
    assert SemanticFieldInferrer.infer_meaning("margin", "number") == "margin"
    assert SemanticFieldInferrer.infer_meaning("customer_id", "id") == "customer_id"
    assert SemanticFieldInferrer.infer_meaning("order_date", "date") == "order_date"


def test_outlier_analytics_detection():
    """Verify OutlierAnalytics flags statistical anomalies using 1.5x IQR and Z-scores."""
    # Data with an extreme transaction
    data = {"id": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"], "amount": [10, 12, 11, 13, 10, 12, 11, 150]}
    df = pd.DataFrame(data)
    outliers = OutlierAnalytics.identify_transaction_outliers(df, "amount", "id")

    assert len(outliers) >= 1
    top_outlier = outliers[0]
    assert top_outlier["identifier"] == "T8"
    assert top_outlier["value"] == 150.0
    assert top_outlier["z_score"] >= 2.0
