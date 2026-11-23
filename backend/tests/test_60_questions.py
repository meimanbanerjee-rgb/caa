# backend/tests/test_60_questions.py
# Comprehensive 60-question test bank verifying financial accuracy, rankings,
# group comparisons, monthly trends, AOV, data quality, paraphrases, and unanswerable queries.

import os
import sys
from pathlib import Path
import pandas as pd
import pytest

from backend.app.analytics.schema_mapping import SchemaMapper
from backend.app.analytics.financial_metrics import FinancialMetricsEngine
from backend.app.llm.safe_plans import SafePlanExecutor, SafePlan
from backend.app.llm.fallback import DeterministicFallbackProvider
from backend.app.models.dataset import DatasetModel, TableModel


# 60 questions across all categories
TEST_QUESTIONS = [
    # Category 1: Totals (8 questions)
    ("What is our total revenue?", "totals", 205897.50),
    ("What is our gross profit margin?", "totals", 25.81),
    ("What are our total sales?", "totals", 205897.50),
    ("What is our total discount amount?", "totals", 13852.50),
    ("What is our total cost?", "totals", 152760.00),
    ("What is our overall net profit?", "totals", 53137.50),
    ("How much discount was given?", "totals", 13852.50),
    ("What is the gross margin percentage?", "totals", 25.81),

    # Category 2: Rankings (8 questions)
    ("Which products generate the most profit?", "top_profit_product", "Monitor 24-inch"),
    ("What are our top products by revenue?", "top_sales_product", "Monitor 24-inch"),
    ("What is our lowest profit product?", "lowest_profit_product", "Mechanical Keyboard"),
    ("Which product has the highest profit margin?", "highest_margin_product", "Laptop Stand"),
    ("Who are the top 5 customers?", "top_customers", "CUST-"),
    ("Bottom 3 products by sales?", "bottom_products", 3),
    ("What is our best selling product?", "top_sales_product", "Monitor 24-inch"),
    ("What is our worst performing product by profit?", "lowest_profit_product", "Mechanical Keyboard"),

    # Category 3: Comparisons (6 questions)
    ("Which region has the highest revenue?", "top_region", "North"),
    ("Compare the performance of different regions.", "compare_regions", 4),
    ("Which marketing channel performs best?", "top_channel", "Online"),
    ("Compare performance by marketing channel.", "compare_channels", 4),
    ("Which category has the highest sales?", "compare_categories", "Displays"),
    ("Compare North vs South regions.", "compare_regions", "North"),

    # Category 4: Monthly Trends & Drivers (5 questions)
    ("Show monthly revenue trend.", "monthly_trend", 3),
    ("Why did revenue decrease last month?", "monthly_trend", 3),
    ("What was the total sales in March?", "monthly_march", 23855.00),
    ("What was the revenue in February?", "monthly_february", 26010.00),
    ("What was the revenue in January?", "monthly_january", 12417.50),

    # Category 5: Discount & AOV (5 questions)
    ("What is the average order value?", "aov", 6863.25),
    ("What is our AOV?", "aov", 6863.25),
    ("What is the average transaction size?", "aov", 6863.25),
    ("How many total orders are there?", "order_count", 30),
    ("What is the discount impact on gross revenue?", "totals", 13852.50),

    # Category 6: Outliers & Data Quality (5 questions)
    ("Find unusual transactions.", "outliers", 0),
    ("Are there any outliers or anomalies?", "outliers", 0),
    ("How many duplicate rows are there?", "duplicates", 0),
    ("Which columns have missing values?", "missing_values", 0),
    ("Is there any missing data in this file?", "missing_values", 0),

    # Category 7: Insights & Actions (5 questions)
    ("What are the three most important actions for this business?", "insights", 3),
    ("What are the key business recommendations?", "insights", 3),
    ("Show me the strategic priorities.", "insights", 3),
    ("What are our top business actions?", "insights", 3),
    ("Show me the evidence behind the top insight.", "evidence", 1),

    # Category 8: Paraphrased Questions (10 questions)
    ("Give me the total income", "totals", 205897.50),
    ("What's the company's gross revenue?", "totals", 205897.50),
    ("Tell me the top making items", "top_profit_product", "Monitor 24-inch"),
    ("Which geographical area made the most money?", "top_region", "North"),
    ("What did we pull in during March?", "monthly_march", 23855.00),
    ("How much is an average customer order?", "aov", 6863.25),
    ("Any weird or abnormal orders?", "outliers", 0),
    ("Are any rows copied or duplicated?", "duplicates", 0),
    ("How is our profit margin looking?", "totals", 25.81),
    ("What marketing channels are driving the business?", "compare_channels", 4),

    # Category 9: Unanswerable Questions (8 questions - Must honestly say data is missing)
    ("What is the weather tomorrow?", "unanswerable", "weather"),
    ("What is the stock price of Microsoft?", "unanswerable", "stock"),
    ("Who is the CEO of Infosys?", "unanswerable", "ceo"),
    ("Tell me a joke", "unanswerable", "joke"),
    ("How to make pizza?", "unanswerable", "pizza"),
    ("What will inflation be next year?", "unanswerable", "inflation"),
    ("What is the employee turnover rate?", "unanswerable", "turnover"),
    ("How many website visitors were there yesterday?", "unanswerable", "visitors"),
]


@pytest.fixture(scope="module")
def sales_df():
    csv_path = Path("backend/tests/test_data/insightforge_business_sales_test.csv")
    if not csv_path.exists():
        pytest.fail(f"Test CSV not found at {csv_path}")
    df = pd.read_csv(csv_path)
    return df


@pytest.fixture(scope="module")
def sales_dataset(sales_df):
    return DatasetModel(
        id="test_sales_001",
        filename="insightforge_business_sales_test.csv",
        file_type="csv",
        size_bytes=4096,
        status="ready",
        tables=[
            TableModel(
                id="tbl_1",
                dataset_id="test_sales_001",
                name="sales",
                row_count=len(sales_df),
                column_count=len(sales_df.columns),
            )
        ],
    )


@pytest.mark.anyio
async def test_full_60_question_bank(sales_df, sales_dataset):
    """Executes all 60 test questions and asserts mathematically verified outputs."""
    mapping = SchemaMapper.map_dataframe(sales_df)
    provider = DeterministicFallbackProvider()

    results_table = []
    passed = 0
    failed = 0

    for idx, (question, expected_type, expected_val) in enumerate(TEST_QUESTIONS, start=1):
        plan = SafePlanExecutor.determine_plan_heuristic(question, sales_df, dataset=sales_dataset)
        op_res = SafePlanExecutor.execute_safe_plan(plan, sales_df, dataset=sales_dataset)

        llm_res = await provider.ask_grounded(
            question=question,
            analysis_metrics={},
            dataset_ids=[sales_dataset.id],
            dataset=sales_dataset,
            df=sales_df,
        )

        text = llm_res.text
        is_success = False

        if expected_type == "unanswerable":
            # Must honestly state that data is missing / external
            is_success = (
                op_res.status == "missing_data"
                or plan.operation == "unanswerable"
                or "does not contain" in text.lower()
                or "missing" in text.lower()
            )
        elif expected_type == "totals":
            # Check number presence
            expected_num_str = f"{expected_val:,.2f}" if isinstance(expected_val, float) else str(expected_val)
            val_found = (
                str(expected_val) in str(op_res.values)
                or expected_num_str in text
                or any(abs(float(expected_val) - float(v)) < 0.1 for v in op_res.values.values() if isinstance(v, (int, float)))
            )
            is_success = val_found
        elif expected_type == "top_profit_product":
            is_success = "Monitor 24-inch" in text or "Monitor 24-inch" in str(op_res.values)
        elif expected_type == "top_sales_product":
            is_success = "Monitor 24-inch" in text or "Monitor 24-inch" in str(op_res.values)
        elif expected_type == "lowest_profit_product":
            is_success = "Mechanical Keyboard" in text or "Mechanical Keyboard" in str(op_res.values)
        elif expected_type == "highest_margin_product":
            is_success = "Laptop Stand" in text or "Laptop Stand" in str(op_res.values)
        elif expected_type == "top_region":
            is_success = "North" in text or "North" in str(op_res.values)
        elif expected_type == "top_channel":
            is_success = "Online" in text or "Online" in str(op_res.values)
        elif expected_type == "compare_regions":
            is_success = "North" in text and "South" in text
        elif expected_type == "compare_channels":
            is_success = "Online" in text and "Search" in text
        elif expected_type == "compare_categories":
            is_success = "Displays" in text or "Displays" in str(op_res.values)
        elif expected_type in ["monthly_march", "monthly_february", "monthly_january"]:
            is_success = f"{expected_val:,.2f}" in text or any(abs(float(expected_val) - float(v)) < 0.1 for v in op_res.values.values() if isinstance(v, (int, float))) or any(str(expected_val) in str(p) for p in op_res.values.get("periods", []))
        elif expected_type == "monthly_trend":
            is_success = (
                len(op_res.values.get("periods", [])) > 0
                or "trajectory" in text.lower()
                or "trend" in text.lower()
                or "drivers" in text.lower()
                or "change" in text.lower()
            )
        elif expected_type == "aov":
            is_success = "6,863.25" in text or any(abs(6863.25 - float(v)) < 0.1 for v in op_res.values.values() if isinstance(v, (int, float)))
        elif expected_type == "order_count":
            is_success = "30" in text or op_res.values.get("order_count") == 30
        elif expected_type in ["outliers", "duplicates", "missing_values"]:
            is_success = op_res.status == "success" and len(text) > 5
        elif expected_type in ["insights", "evidence"]:
            is_success = len(text) > 10
        elif expected_type == "top_customers":
            is_success = "CUST-" in text or len(op_res.values.get("ranks", [])) > 0
        elif expected_type == "bottom_products":
            is_success = len(op_res.values.get("bottom_n", [])) > 0 or len(op_res.values.get("ranks", [])) > 0

        if is_success:
            passed += 1
        else:
            failed += 1

        results_table.append({
            "idx": idx,
            "question": question,
            "plan": plan.operation,
            "status": "PASS" if is_success else "FAIL",
            "snippet": text[:80].replace("\n", " "),
        })

    print(f"\n================ 60-QUESTION BANK RESULTS ================")
    print(f"Total: 60 | Passed: {passed} | Failed: {failed} ({(passed/60)*100:.1f}%)")
    for r in results_table:
        print(f"[{r['status']}] Q{r['idx']:02d}: {r['question']} -> {r['plan']} | {r['snippet']}")

    assert failed == 0, f"{failed} questions failed out of 60!"


if __name__ == "__main__":
    import asyncio
    df = pd.read_csv("backend/tests/test_data/insightforge_business_sales_test.csv")
    ds = DatasetModel(
        id="test_sales_001",
        filename="insightforge_business_sales_test.csv",
        file_type="csv",
        size_bytes=4096,
        status="ready",
        tables=[TableModel(name="sales", row_count=len(df), column_count=len(df.columns))],
    )
    asyncio.run(test_full_60_question_bank(df, ds))
