# backend/app/analytics/__init__.py
# Analytics Pipeline Orchestrator executing deterministic pandas computations (FR-12, FR-13).
# Integrates SchemaMapper, FinancialMetricsEngine, and CapabilityRegistry for verifiable analysis.

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from backend.app.config import settings
from backend.app.models.dataset import DatasetModel, TableModel
from backend.app.profiling.column_types import ColumnTypeDetector
from backend.app.profiling.semantic_fields import SemanticFieldInferrer
from backend.app.profiling.quality_checks import QualityProfiler
from backend.app.analytics.descriptive import DescriptiveAnalytics
from backend.app.analytics.financial import FinancialAnalytics
from backend.app.analytics.timeseries import TimeSeriesAnalytics
from backend.app.analytics.outliers import OutlierAnalytics
from backend.app.analytics.schema_mapping import SchemaMapper
from backend.app.analytics.financial_metrics import FinancialMetricsEngine
from backend.app.analytics.capability_registry import CapabilityRegistry


def load_dataset_dataframe(dataset: DatasetModel) -> Optional[pd.DataFrame]:
    """Loads dataset into a Pandas DataFrame from disk or from sample rows."""
    file_path = None
    if settings.uploads_dir.exists():
        candidates = list(settings.uploads_dir.glob(f"{dataset.id}_*"))
        if candidates:
            file_path = candidates[0]

    if file_path and file_path.exists():
        ext = file_path.suffix.lower()
        if ext in [".csv", ".tsv", ".txt"]:
            from backend.app.ingestion.csv_parser import CsvParser
            enc, sep = CsvParser.detect_encoding_and_delimiter(file_path)
            return pd.read_csv(file_path, encoding=enc, sep=sep, low_memory=False)
        elif ext == ".xlsx":
            return pd.read_excel(file_path, data_only=True)
        elif ext in [".json", ".jsonl"]:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                if ext == ".jsonl":
                    lines = [json.loads(l) for l in f if l.strip()]
                    return pd.json_normalize(lines)
                else:
                    data = json.load(f)
                    return pd.json_normalize(data if isinstance(data, list) else [data])
        elif ext == ".pdf":
            from backend.app.ingestion.pdf_parser import PdfParser
            tables, _ = PdfParser.parse(file_path, dataset_id=dataset.id)
            for t in tables:
                if t.name.startswith("Extracted Table") and t.sample_rows:
                    return pd.DataFrame(t.sample_rows)
            if tables and tables[0].sample_rows:
                return pd.DataFrame(tables[0].sample_rows)

    # Fallback to sample rows if disk file unavailable
    if dataset.tables and dataset.tables[0].sample_rows:
        return pd.DataFrame(dataset.tables[0].sample_rows)

    return None


def run_analytics_pipeline(dataset: DatasetModel) -> Dict[str, Any]:
    """
    Executes complete deterministic analytics pipeline on dataset.
    FR-12: Executes only analyses supported by present columns.
    Returns: Dict containing 'metrics', 'charts', 'domain', 'supported_features'.
    """
    df = load_dataset_dataframe(dataset)
    if df is None or df.empty:
        return {
            "metrics": {
                "dataset_name": dataset.filename,
                "row_count": 0,
                "column_count": 0,
                "note": "Empty dataset",
            },
            "charts": [],
            "domain": "general",
            "supported_features": [],
        }

    # Clean columns
    df.columns = [str(c).strip() for c in df.columns]
    column_names = list(df.columns)
    domain = SemanticFieldInferrer.guess_domain(column_names)

    # Map column semantic meanings
    field_map: Dict[str, str] = {}
    numeric_cols: List[str] = []
    date_col: Optional[str] = None
    category_col: Optional[str] = None
    region_col: Optional[str] = None
    product_col: Optional[str] = None
    customer_col: Optional[str] = None

    for col in column_names:
        series = df[col]
        detected_type = ColumnTypeDetector.detect_type(series, col)
        if detected_type == "number":
            numeric_cols.append(col)
        elif detected_type == "date" and not date_col:
            date_col = col

        meaning = SemanticFieldInferrer.infer_meaning(col, detected_type)
        if meaning:
            field_map[meaning] = col
            if meaning == "category" and not category_col:
                category_col = col
            elif meaning == "region" and not region_col:
                region_col = col
            elif meaning == "product_name" and not product_col:
                product_col = col
            elif meaning == "customer_id" and not customer_col:
                customer_col = col

    # Map schema using robust synonym dictionary and canonical roles
    schema_map = SchemaMapper.map_dataframe(df)

    # Check for revenue or derived revenue (quantity * unit_price)
    has_financials = (
        schema_map.has_role("net_sales")
        or (schema_map.has_role("quantity") and schema_map.has_role("unit_price"))
        or "revenue" in field_map
    )

    date_col = schema_map.get_col("date") or date_col
    product_col = schema_map.get_col("product") or product_col
    customer_col = schema_map.get_col("customer") or customer_col
    category_col = schema_map.get_col("category") or category_col
    region_col = schema_map.get_col("region") or region_col

    metrics: Dict[str, Any] = {
        "dataset_name": dataset.filename,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
    }
    charts: List[Dict[str, Any]] = []
    supported_features: List[str] = ["descriptive_statistics"]

    # 1. Descriptive Summary Stats
    summary_stats = DescriptiveAnalytics.compute_summary_stats(df, numeric_cols)
    metrics["descriptive_stats"] = summary_stats

    # 2. Financial Analytics Engine (FR-12, FR-13)
    if has_financials:
        supported_features.append("financial_metrics")
        try:
            df_fin = FinancialMetricsEngine.compute_row_financials(df, schema_map)
            totals = FinancialMetricsEngine.summarize_totals(df_fin)
            metrics.update(totals)

            # Top Products & Rankings
            if product_col:
                agg_prod = FinancialMetricsEngine.aggregate_by(df_fin, product_col)
                top_prods = FinancialMetricsEngine.rank_entities(agg_prod, product_col, metric="profit", limit=5)
                bottom_prods = FinancialMetricsEngine.rank_entities(agg_prod, product_col, metric="profit", ascending=True, limit=5)
                metrics["top_products"] = top_prods
                metrics["bottom_products"] = bottom_prods
                supported_features.append("product_rankings")

            # Top Customers
            if customer_col:
                agg_cust = FinancialMetricsEngine.aggregate_by(df_fin, customer_col)
                top_custs = FinancialMetricsEngine.rank_entities(agg_cust, customer_col, metric="net_sales", limit=5)
                metrics["top_customers"] = top_custs
                supported_features.append("customer_rankings")

            # Category / Region Breakdown
            chosen_cat = category_col or region_col
            if chosen_cat:
                agg_cat = FinancialMetricsEngine.aggregate_by(df_fin, chosen_cat)
                cat_breakdown = [
                    {
                        "category": str(r[chosen_cat]),
                        "value": round(float(r["net_sales"]), 2),
                        "percentage": round(float(r["revenue_share_pct"]), 2),
                        "percentage_of_total": round(float(r["revenue_share_pct"]), 2),
                    }
                    for _, r in agg_cat.iterrows()
                ]
                metrics["category_breakdown"] = cat_breakdown
                charts.append({
                    "type": "bar",
                    "title": f"Revenue by {chosen_cat.title()}",
                    "data": cat_breakdown,
                    "x_key": "category",
                    "y_key": "value",
                })
                supported_features.append("category_breakdown")

            # Outlier Transactions on net sales
            outliers = OutlierAnalytics.identify_transaction_outliers(
                df=df_fin,
                value_col="calc_net_sales",
                id_col=customer_col or product_col or column_names[0],
                top_k=5,
            )
            metrics["revenue_outliers"] = outliers
            if outliers:
                supported_features.append("outlier_detection")

            # Time-Series Monthly Trend
            if date_col:
                monthly_trend = FinancialMetricsEngine.compute_monthly_trend(df_fin, date_col)
                metrics["time_series_growth"] = {
                    "periods": monthly_trend,
                    "overall_growth_rate": monthly_trend[-1]["growth_percentage"] if monthly_trend else None,
                    "trend_direction": "up" if monthly_trend and (monthly_trend[-1]["growth_percentage"] or 0) > 0 else "down",
                }
                if monthly_trend:
                    charts.append({
                        "type": "line",
                        "title": "Monthly Revenue Trend",
                        "data": monthly_trend,
                        "x_key": "period",
                        "y_key": "net_sales",
                    })
                    supported_features.append("time_series_growth")

        except Exception as fin_err:
            # Fallback to legacy financial computation if row derivation fails
            if "revenue" in field_map:
                rev_col = field_map["revenue"]
                financial = FinancialAnalytics.compute_margins_and_profit(
                    df=df,
                    revenue_col=rev_col,
                    cost_col=field_map.get("cost"),
                    units_col=field_map.get("units_sold"),
                    margin_col=field_map.get("margin"),
                )
                metrics.update(financial)

    # 3. Dynamic Suggested Questions based on verified capabilities
    metrics["suggested_questions"] = CapabilityRegistry.generate_suggested_questions(schema_map)

    return {
        "metrics": metrics,
        "charts": charts,
        "domain": domain,
        "supported_features": supported_features,
    }
