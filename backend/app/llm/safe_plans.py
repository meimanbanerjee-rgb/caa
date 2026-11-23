# backend/app/llm/safe_plans.py
# Fixed list of validated deterministic Pandas operations and safe plan schemas.
# Never executes dynamic arbitrary Python or shell code (FR-18).

from typing import Any, Dict, List, Optional, Tuple
import re
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


ALLOWED_OPERATIONS = [
    "total",
    "financial_totals",
    "average",
    "average_order_value",
    "count",
    "group_by_sum",
    "top_n",
    "bottom_n",
    "compare_groups",
    "period_over_period_change",
    "monthly_trend",
    "top_drivers_of_change",
    "find_outliers",
    "missing_values_report",
    "duplicate_report",
    "list_top_insights",
    "get_insight_evidence",
    "unanswerable",
]


class SafePlan(BaseModel):
    """Structured, Pydantic-validated safe operation plan chosen by LLM or fallback."""
    operation: str
    target_column: Optional[str] = None
    group_column: Optional[str] = None
    metric_column: Optional[str] = None
    top_n: int = 5
    filters: Dict[str, Any] = Field(default_factory=dict)
    time_range: Optional[str] = None
    insight_id: Optional[str] = None


class OperationResult(BaseModel):
    """Normalized structured result returned by every deterministic analysis operation."""
    operation: str
    status: str = "success"  # 'success', 'missing_data', 'clarification_needed', 'error'
    values: Dict[str, Any] = Field(default_factory=dict)
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    table_payload: Optional[List[Dict[str, Any]]] = None
    chart_payload: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Individual Small Validated Pandas Functions
# ---------------------------------------------------------------------------

def apply_filters(df: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> pd.DataFrame:
    """Safely applies equality or substring filters to a DataFrame."""
    if not filters or df.empty:
        return df
    filtered = df.copy()
    for col, val in filters.items():
        if col in filtered.columns and val is not None:
            if isinstance(val, (int, float)):
                filtered = filtered[filtered[col] == val]
            else:
                filtered = filtered[filtered[col].astype(str).str.contains(str(val), case=False, na=False)]
    return filtered


def op_total(
    df: pd.DataFrame,
    col: str,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Computes total sum of a numeric column with optional row filtering."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    if col not in df.columns:
        return OperationResult(
            operation="total",
            status="missing_data",
            missing_fields=[col],
            source_references=src,
            limitations=[f"Column '{col}' is not present in the dataset."],
        )

    work_df = apply_filters(df, filters)
    series = pd.to_numeric(work_df[col], errors="coerce").dropna()
    total_val = float(series.sum())
    count_val = int(len(series))

    values: Dict[str, Any] = {
        "column": col,
        "total": round(total_val, 2),
        "total_revenue": round(total_val, 2),
        "count": count_val,
        "filters_applied": filters or {},
    }

    # If margin or profit exists in df, compute gross margin percentage as well
    for m_col in ["margin", "gross_profit", "profit"]:
        if m_col in work_df.columns:
            tot_margin = float(pd.to_numeric(work_df[m_col], errors="coerce").fillna(0).sum())
            margin_pct = round((tot_margin / total_val * 100.0), 2) if total_val > 0 else 0.0
            values["gross_profit"] = round(tot_margin, 2)
            values["gross_margin_percentage"] = margin_pct
            break

    return OperationResult(
        operation="total",
        status="success",
        values=values,
        source_references=src,
        limitations=["Calculated strictly by Python pandas; missing and non-numeric values excluded."],
    )


def op_average(
    df: pd.DataFrame,
    col: str,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Computes arithmetic mean of a numeric column."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    if col not in df.columns:
        return OperationResult(
            operation="average",
            status="missing_data",
            missing_fields=[col],
            source_references=src,
            limitations=[f"Column '{col}' is missing."],
        )

    work_df = apply_filters(df, filters)
    series = pd.to_numeric(work_df[col], errors="coerce").dropna()
    avg_val = float(series.mean()) if not series.empty else 0.0

    return OperationResult(
        operation="average",
        status="success",
        values={
            "column": col,
            "average": round(avg_val, 2),
            "count": int(len(series)),
        },
        source_references=src,
        limitations=["Arithmetic mean computed from verified numerical records."],
    )


def op_count(
    df: pd.DataFrame,
    col: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Computes total row count or distinct value count of a column."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    work_df = apply_filters(df, filters)

    if col and col in work_df.columns:
        distinct = int(work_df[col].nunique(dropna=True))
        non_null = int(work_df[col].count())
        values = {"column": col, "distinct_count": distinct, "non_null_count": non_null, "total_rows": len(work_df)}
    else:
        values = {"total_rows": len(work_df), "total_columns": len(work_df.columns)}

    return OperationResult(
        operation="count",
        status="success",
        values=values,
        source_references=src,
    )


def op_group_by_sum(
    df: pd.DataFrame,
    group_col: str,
    val_col: str,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Aggregates the sum of val_col grouped by distinct values in group_col."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    missing = [c for c in [group_col, val_col] if c not in df.columns]
    if missing:
        return OperationResult(
            operation="group_by_sum",
            status="missing_data",
            missing_fields=missing,
            source_references=src,
            limitations=[f"Required columns missing: {', '.join(missing)}"],
        )

    work_df = apply_filters(df, filters).copy()
    work_df[val_col] = pd.to_numeric(work_df[val_col], errors="coerce").fillna(0)
    grouped = work_df.groupby(group_col, as_index=False)[val_col].sum()
    grouped = grouped.sort_values(by=val_col, ascending=False)

    total_val = float(grouped[val_col].sum())
    results: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        cat_name = str(row[group_col])
        v = float(row[val_col])
        share = round((v / total_val * 100.0), 2) if total_val > 0 else 0.0
        results.append({"name": cat_name, "value": round(v, 2), "percentage": share})

    top_entry = results[0] if results else None

    return OperationResult(
        operation="group_by_sum",
        status="success",
        values={
            "group_column": group_col,
            "metric_column": val_col,
            "total": round(total_val, 2),
            "highest": top_entry,
            "breakdown": results,
        },
        table_payload=results,
        chart_payload={
            "type": "bar",
            "title": f"Sum of {val_col.title()} by {group_col.title()}",
            "data": results,
            "x_key": "name",
            "y_key": "value",
        },
        source_references=src,
    )


def op_top_n(
    df: pd.DataFrame,
    entity_col: str,
    val_col: str,
    n: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Ranks top N entities by total sum of val_col."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    missing = [c for c in [entity_col, val_col] if c not in df.columns]
    if missing:
        return OperationResult(
            operation="top_n",
            status="missing_data",
            missing_fields=missing,
            source_references=src,
        )

    work_df = apply_filters(df, filters).copy()
    work_df[val_col] = pd.to_numeric(work_df[val_col], errors="coerce").fillna(0)
    grouped = work_df.groupby(entity_col, as_index=False)[val_col].sum()
    grouped = grouped.sort_values(by=val_col, ascending=False).head(max(1, n))

    items = [
        {"rank": idx + 1, "name": str(r[entity_col]), "value": round(float(r[val_col]), 2)}
        for idx, (_, r) in enumerate(grouped.iterrows())
    ]

    return OperationResult(
        operation="top_n",
        status="success",
        values={
            "entity_column": entity_col,
            "metric_column": val_col,
            "top_n": items,
            "count": len(items),
        },
        table_payload=items,
        source_references=src,
    )


def op_bottom_n(
    df: pd.DataFrame,
    entity_col: str,
    val_col: str,
    n: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Ranks bottom N entities with lowest sum of val_col."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    missing = [c for c in [entity_col, val_col] if c not in df.columns]
    if missing:
        return OperationResult(
            operation="bottom_n",
            status="missing_data",
            missing_fields=missing,
            source_references=src,
        )

    work_df = apply_filters(df, filters).copy()
    work_df[val_col] = pd.to_numeric(work_df[val_col], errors="coerce").fillna(0)
    grouped = work_df.groupby(entity_col, as_index=False)[val_col].sum()
    grouped = grouped.sort_values(by=val_col, ascending=True).head(max(1, n))

    items = [
        {"rank": idx + 1, "name": str(r[entity_col]), "value": round(float(r[val_col]), 2)}
        for idx, (_, r) in enumerate(grouped.iterrows())
    ]

    return OperationResult(
        operation="bottom_n",
        status="success",
        values={
            "entity_column": entity_col,
            "metric_column": val_col,
            "bottom_n": items,
        },
        table_payload=items,
        source_references=src,
    )


def op_compare_groups(
    df: pd.DataFrame,
    group_col: str,
    metric_cols: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Compares multiple performance metrics across categories in group_col."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    if group_col not in df.columns:
        return OperationResult(
            operation="compare_groups",
            status="missing_data",
            missing_fields=[group_col],
            source_references=src,
        )

    work_df = apply_filters(df, filters).copy()
    if not metric_cols:
        metric_cols = [c for c in work_df.columns if pd.api.types.is_numeric_dtype(work_df[c])]

    valid_metrics = [m for m in metric_cols if m in work_df.columns]
    if not valid_metrics:
        return OperationResult(
            operation="compare_groups",
            status="missing_data",
            missing_fields=["numeric_metrics"],
            source_references=src,
        )

    for m in valid_metrics:
        work_df[m] = pd.to_numeric(work_df[m], errors="coerce").fillna(0)

    grouped = work_df.groupby(group_col, as_index=False)[valid_metrics].sum()
    comparison_table = grouped.to_dict(orient="records")

    return OperationResult(
        operation="compare_groups",
        status="success",
        values={
            "group_column": group_col,
            "metrics": valid_metrics,
            "groups": comparison_table,
        },
        table_payload=comparison_table,
        source_references=src,
    )


def op_monthly_trend(
    df: pd.DataFrame,
    date_col: str,
    val_col: str,
    month_filter: Optional[str] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Computes monthly aggregated trend and allows specific month extraction (e.g. March)."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    missing = [c for c in [date_col, val_col] if c not in df.columns]
    if missing:
        return OperationResult(
            operation="monthly_trend",
            status="missing_data",
            missing_fields=missing,
            source_references=src,
        )

    work_df = df.copy()
    work_df["_dt"] = pd.to_datetime(work_df[date_col], errors="coerce")
    work_df = work_df.dropna(subset=["_dt"]).copy()
    work_df[val_col] = pd.to_numeric(work_df[val_col], errors="coerce").fillna(0)

    work_df["period"] = work_df["_dt"].dt.strftime("%Y-%m")
    work_df["month_name"] = work_df["_dt"].dt.strftime("%B")

    monthly = work_df.groupby(["period", "month_name"], as_index=False)[val_col].sum()
    monthly = monthly.sort_values(by="period")

    periods_list: List[Dict[str, Any]] = []
    for _, r in monthly.iterrows():
        periods_list.append({
            "period": str(r["period"]),
            "month_name": str(r["month_name"]),
            "value": round(float(r[val_col]), 2),
        })

    month_result: Optional[Dict[str, Any]] = None
    if month_filter:
        clean_target = month_filter.lower().strip()
        for p in periods_list:
            if clean_target in p["period"].lower() or clean_target in p["month_name"].lower():
                month_result = p
                break

    return OperationResult(
        operation="monthly_trend",
        status="success",
        values={
            "date_column": date_col,
            "metric_column": val_col,
            "periods": periods_list,
            "filtered_month": month_result,
        },
        table_payload=periods_list,
        chart_payload={
            "type": "line",
            "title": f"Monthly Trend for {val_col.title()}",
            "data": periods_list,
            "x_key": "period",
            "y_key": "value",
        },
        source_references=src,
    )


def op_period_over_period_change(
    df: pd.DataFrame,
    date_col: str,
    val_col: str,
    period: str = "monthly",
    filters: Optional[Dict[str, Any]] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Calculates sequential growth rate and absolute changes between periods."""
    res = op_monthly_trend(df, date_col, val_col, source_info=source_info)
    if res.status != "success":
        return res

    periods = res.values.get("periods", [])
    if len(periods) < 2:
        return OperationResult(
            operation="period_over_period_change",
            status="missing_data",
            missing_fields=["multiple_periods"],
            limitations=["At least 2 chronological periods required for period-over-period comparison."],
        )

    changes: List[Dict[str, Any]] = []
    for i in range(1, len(periods)):
        prev_p = periods[i - 1]
        curr_p = periods[i]
        diff = curr_p["value"] - prev_p["value"]
        pct = (diff / prev_p["value"] * 100.0) if prev_p["value"] != 0 else 0.0
        changes.append({
            "from_period": prev_p["period"],
            "to_period": curr_p["period"],
            "previous_value": prev_p["value"],
            "current_value": curr_p["value"],
            "absolute_change": round(diff, 2),
            "percentage_change": round(pct, 2),
        })

    last_change = changes[-1]

    return OperationResult(
        operation="period_over_period_change",
        status="success",
        values={
            "recent_change": last_change,
            "all_period_changes": changes,
        },
        table_payload=changes,
        source_references=res.source_references,
    )


def op_top_drivers_of_change(
    df: pd.DataFrame,
    date_col: str,
    dim_col: str,
    val_col: str,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Determines which dimension items (products, categories) drove the most recent period change."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    missing = [c for c in [date_col, dim_col, val_col] if c not in df.columns]
    if missing:
        return OperationResult(
            operation="top_drivers_of_change",
            status="missing_data",
            missing_fields=missing,
            source_references=src,
        )

    work_df = df.copy()
    work_df["_dt"] = pd.to_datetime(work_df[date_col], errors="coerce")
    work_df = work_df.dropna(subset=["_dt"]).copy()
    work_df["period"] = work_df["_dt"].dt.strftime("%Y-%m")
    work_df[val_col] = pd.to_numeric(work_df[val_col], errors="coerce").fillna(0)

    periods = sorted(work_df["period"].unique())
    if len(periods) < 2:
        return OperationResult(
            operation="top_drivers_of_change",
            status="missing_data",
            missing_fields=["multiple_periods"],
            limitations=["At least two chronological months required to diagnose changes."],
        )

    prev_p = periods[-2]
    curr_p = periods[-1]

    prev_df = work_df[work_df["period"] == prev_p].groupby(dim_col)[val_col].sum()
    curr_df = work_df[work_df["period"] == curr_p].groupby(dim_col)[val_col].sum()

    all_dims = sorted(list(set(prev_df.index) | set(curr_df.index)))
    driver_rows: List[Dict[str, Any]] = []

    for d in all_dims:
        pv = float(prev_df.get(d, 0.0))
        cv = float(curr_df.get(d, 0.0))
        diff = cv - pv
        driver_rows.append({
            "item": str(d),
            "prev_period": round(pv, 2),
            "curr_period": round(cv, 2),
            "absolute_diff": round(diff, 2),
        })

    # Sort by absolute difference
    driver_rows.sort(key=lambda x: x["absolute_diff"])

    return OperationResult(
        operation="top_drivers_of_change",
        status="success",
        values={
            "dimension": dim_col,
            "from_period": prev_p,
            "to_period": curr_p,
            "drivers": driver_rows,
            "biggest_drag": driver_rows[0] if driver_rows else None,
            "biggest_gain": driver_rows[-1] if driver_rows else None,
        },
        table_payload=driver_rows,
        source_references=src,
    )


def op_find_outliers(
    df: pd.DataFrame,
    val_col: str,
    id_col: Optional[str] = None,
    z_thresh: float = 2.0,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Identifies statistical outlier records exceeding z_thresh standard deviations."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    if val_col not in df.columns:
        return OperationResult(
            operation="find_outliers",
            status="missing_data",
            missing_fields=[val_col],
            source_references=src,
        )

    series = pd.to_numeric(df[val_col], errors="coerce").dropna()
    mean = float(series.mean())
    std = float(series.std(ddof=0))

    outliers_list: List[Dict[str, Any]] = []
    if std > 0:
        z_scores = (series - mean).abs() / std
        outlier_indices = z_scores[z_scores >= z_thresh].index.tolist()

        for idx in outlier_indices:
            row = df.loc[idx]
            ident = str(row[id_col]) if id_col and id_col in df.columns else f"Row {idx + 1}"
            outliers_list.append({
                "row_index": int(idx) + 1,
                "identifier": ident,
                "value": round(float(row[val_col]), 2),
                "z_score": round(float(z_scores.loc[idx]), 2),
            })

    return OperationResult(
        operation="find_outliers",
        status="success",
        values={
            "metric_column": val_col,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "outliers_found": len(outliers_list),
            "outliers": outliers_list,
        },
        table_payload=outliers_list,
        source_references=src,
    )


def op_missing_values_report(
    df: pd.DataFrame,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Generates per-column report of missing / null values."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    total_rows = len(df)
    report: List[Dict[str, Any]] = []

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        pct = round(null_count / total_rows * 100.0, 2) if total_rows > 0 else 0.0
        report.append({
            "column": str(col),
            "null_count": null_count,
            "percentage": pct,
        })

    cols_with_missing = [r for r in report if r["null_count"] > 0]

    return OperationResult(
        operation="missing_values_report",
        status="success",
        values={
            "total_rows": total_rows,
            "columns_with_missing": cols_with_missing,
            "all_columns_clean": len(cols_with_missing) == 0,
            "report": report,
        },
        table_payload=report,
        source_references=src,
    )


def op_duplicate_report(
    df: pd.DataFrame,
    source_info: Optional[Dict[str, Any]] = None,
) -> OperationResult:
    """Computes exact duplicate row count across all columns."""
    src = [source_info or {"sheet": "default", "rows": f"1-{len(df)}"}]
    dup_count = int(df.duplicated().sum())
    total_rows = len(df)

    return OperationResult(
        operation="duplicate_report",
        status="success",
        values={
            "total_rows": total_rows,
            "duplicate_count": dup_count,
            "is_clean": dup_count == 0,
        },
        source_references=src,
    )


def op_list_top_insights(
    insights: List[Any],
    n: int = 3,
) -> OperationResult:
    """Retrieves top prioritized concrete business insights and recommended actions."""
    if not insights:
        return OperationResult(
            operation="list_top_insights",
            status="missing_data",
            missing_fields=["insights"],
            limitations=["No synthesized insights are associated with this analysis."],
        )

    # Sort by priority order: critical, high, medium, low
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_insights = sorted(
        insights,
        key=lambda x: priority_order.get(getattr(x, "priority", "medium").lower(), 2),
    )

    top_items = []
    for item in sorted_insights[:n]:
        top_items.append({
            "id": getattr(item, "id", ""),
            "title": getattr(item, "title", "Insight"),
            "priority": getattr(item, "priority", "high"),
            "observed_fact": getattr(item, "observed_fact", ""),
            "recommendation": getattr(item, "recommendation", ""),
        })

    return OperationResult(
        operation="list_top_insights",
        status="success",
        values={
            "count": len(top_items),
            "top_actions": top_items,
        },
        table_payload=top_items,
    )


def op_get_insight_evidence(
    insights: List[Any],
    insight_id: Optional[str] = None,
) -> OperationResult:
    """Extracts verifiable mathematical evidence, formulas, and source rows for an insight."""
    if not insights:
        return OperationResult(
            operation="get_insight_evidence",
            status="missing_data",
            missing_fields=["insights"],
        )

    target = None
    if insight_id:
        target = next((i for i in insights if getattr(i, "id", "") == insight_id), None)
    if not target:
        target = insights[0]

    src = getattr(target, "source", None)
    source_ref = {
        "filename": getattr(src, "filename", "dataset"),
        "sheet": getattr(src, "sheet", "default"),
        "row_range": getattr(src, "row_range", "all"),
    } if src else {"sheet": "default"}

    return OperationResult(
        operation="get_insight_evidence",
        status="success",
        values={
            "insight_id": getattr(target, "id", ""),
            "title": getattr(target, "title", ""),
            "observed_fact": getattr(target, "observed_fact", ""),
            "formula": getattr(target, "method_or_formula", ""),
            "evidence": getattr(target, "evidence", {}),
            "assumptions": getattr(target, "assumptions_and_limitations", []),
        },
        source_references=[source_ref],
    )


# ---------------------------------------------------------------------------
# Safe Plan Execution & Deterministic Heuristic Mapping
# ---------------------------------------------------------------------------

class SafePlanExecutor:
    """Dispatches validated SafePlan to specific pandas operation functions."""

    @classmethod
    def execute_safe_plan(
        cls,
        plan: SafePlan,
        df: pd.DataFrame,
        analysis: Optional[Any] = None,
        dataset: Optional[Any] = None,
    ) -> OperationResult:
        """Executes a validated SafePlan against the DataFrame and analysis snapshot."""
        src_info = {
            "filename": getattr(dataset, "filename", "dataset.csv") if dataset else "dataset.csv",
            "sheet": getattr(dataset.tables[0], "name", "Sheet1") if (dataset and getattr(dataset, "tables", None)) else "default",
            "rows": f"1-{len(df)}",
        }

        if df is None or df.empty:
            return OperationResult(
                operation=plan.operation,
                status="missing_data",
                source_references=[src_info],
                limitations=["The dataset contains no records."],
            )

        from backend.app.analytics.schema_mapping import SchemaMapper
        from backend.app.analytics.financial_metrics import FinancialMetricsEngine, MissingFieldError
        mapping = SchemaMapper.map_dataframe(df)

        op = plan.operation

        # 1. Unanswerable check
        if op == "unanswerable":
            return OperationResult(
                operation="unanswerable",
                status="missing_data",
                missing_fields=["requested_external_domain"],
                source_references=[src_info],
                limitations=["The requested topic is outside the scope of this business dataset."],
            )

        # 2. Financial totals (or total on revenue/profit/cost)
        if op in ["financial_totals", "total"]:
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                totals = FinancialMetricsEngine.summarize_totals(df_fin)
                return OperationResult(
                    operation=op,
                    status="success",
                    values=totals,
                    source_references=[src_info],
                    limitations=["Calculated strictly by Python pandas; Group margins calculated as SUM(profit)/SUM(net_sales)*100."],
                )
            except MissingFieldError as mfe:
                if plan.target_column and plan.target_column in df.columns:
                    return op_total(df, plan.target_column, filters=plan.filters, source_info=src_info)
                return OperationResult(
                    operation="financial_totals",
                    status="missing_data",
                    missing_fields=mfe.missing_roles,
                    source_references=[src_info],
                    limitations=[mfe.message],
                )

        # 3. Average Order Value (AOV)
        if op in ["average_order_value", "average"]:
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                aov = FinancialMetricsEngine.compute_aov(df_fin, order_id_col=mapping.get_col("order_id"))
                return OperationResult(
                    operation=op,
                    status="success",
                    values={
                        "average": aov["average_order_value"],
                        "average_order_value": aov["average_order_value"],
                        "count": aov["order_count"],
                        "order_count": aov["order_count"],
                        "total": aov["total_net_sales"],
                        "total_net_sales": aov["total_net_sales"],
                        "column": "revenue",
                    },
                    source_references=[src_info],
                    limitations=["AOV calculated strictly by Python pandas as Total Net Sales / Total Orders."],
                )
            except MissingFieldError as mfe:
                if plan.target_column and plan.target_column in df.columns:
                    return op_average(df, plan.target_column, filters=plan.filters, source_info=src_info)
                return OperationResult(
                    operation="average_order_value",
                    status="missing_data",
                    missing_fields=mfe.missing_roles,
                    source_references=[src_info],
                    limitations=[mfe.message],
                )

        # 4. Top N / Bottom N rankings
        if op in ["top_n", "bottom_n"]:
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                target = plan.target_column or plan.group_column
                if not target or target.lower() in ["product", "product_name", "item", "item_name"]:
                    target = mapping.get_col("product") or target
                elif target.lower() in ["region", "territory"]:
                    target = mapping.get_col("region") or target
                elif target.lower() in ["channel", "marketing_channel"]:
                    target = mapping.get_col("marketing_channel") or target
                elif target.lower() in ["customer", "customer_id", "client"]:
                    target = mapping.get_col("customer") or target

                if not target or target not in df_fin.columns:
                    target = mapping.get_col("product") or mapping.get_col("category") or mapping.get_col("region") or df.columns[0]

                metric = plan.metric_column or "net_sales"
                ascending = (op == "bottom_n")
                agg = FinancialMetricsEngine.aggregate_by(df_fin, target)
                ranks = FinancialMetricsEngine.rank_entities(agg, target, metric=metric, ascending=ascending, limit=plan.top_n or 5)

                formatted_ranks = []
                for i, r in enumerate(ranks, start=1):
                    item = dict(r)
                    item["rank"] = i
                    formatted_ranks.append(item)

                chart = {
                    "type": "bar",
                    "title": f"{'Top' if not ascending else 'Bottom'} {target} by {metric}",
                    "data": formatted_ranks,
                    "x_key": "name",
                    "y_key": "value",
                }

                return OperationResult(
                    operation=op,
                    status="success",
                    values={
                        "entity_column": target,
                        "metric_column": metric,
                        "top_n" if not ascending else "bottom_n": formatted_ranks,
                        "ranks": formatted_ranks,
                        "count": len(formatted_ranks),
                    },
                    table_payload=formatted_ranks,
                    chart_payload=chart,
                    source_references=[src_info],
                    limitations=["Calculated strictly by Python pandas; ties broken alphabetically A-Z."],
                )
            except Exception:
                ent = plan.target_column or plan.group_column or "product_name"
                met = plan.metric_column or "revenue"
                if op == "bottom_n":
                    return op_bottom_n(df, ent, met, n=plan.top_n or 5, filters=plan.filters, source_info=src_info)
                return op_top_n(df, ent, met, n=plan.top_n or 5, filters=plan.filters, source_info=src_info)

        # 5. Group Comparisons / group_by_sum
        if op in ["compare_groups", "group_by_sum"]:
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                grp = plan.group_column
                if not grp or grp.lower() in ["region", "territory"]:
                    grp = mapping.get_col("region") or grp
                elif grp.lower() in ["channel", "marketing_channel"]:
                    grp = mapping.get_col("marketing_channel") or grp
                elif grp.lower() in ["category", "segment"]:
                    grp = mapping.get_col("category") or grp

                if not grp or grp not in df_fin.columns:
                    grp = mapping.get_col("region") or mapping.get_col("category") or df.columns[0]

                agg = FinancialMetricsEngine.aggregate_by(df_fin, grp)
                groups_list = agg.to_dict(orient="records")

                sorted_agg = agg.sort_values(by="net_sales", ascending=False)
                highest_row = sorted_agg.iloc[0] if not sorted_agg.empty else None
                highest_info = None
                if highest_row is not None:
                    highest_info = {
                        "name": str(highest_row[grp]),
                        "value": round(float(highest_row["net_sales"]), 2),
                        "profit": round(float(highest_row["profit"]), 2),
                        "profit_margin_percentage": round(float(highest_row["profit_margin_percentage"]), 2),
                        "percentage": round(float(highest_row["revenue_share_pct"]), 2),
                    }

                chart = {
                    "type": "bar",
                    "title": f"Performance Comparison by {grp}",
                    "data": [
                        {"name": str(r[grp]), "net_sales": round(float(r["net_sales"]), 2), "profit": round(float(r["profit"]), 2)}
                        for r in groups_list
                    ],
                    "x_key": "name",
                    "y_key": "net_sales",
                }

                return OperationResult(
                    operation=op,
                    status="success",
                    values={
                        "group_column": grp,
                        "metric_column": plan.metric_column or "revenue",
                        "groups": groups_list,
                        "breakdown": [
                            {"name": str(r[grp]), "value": round(float(r["net_sales"]), 2), "percentage": round(float(r["revenue_share_pct"]), 2)}
                            for r in groups_list
                        ],
                        "highest": highest_info,
                    },
                    table_payload=groups_list,
                    chart_payload=chart,
                    source_references=[src_info],
                    limitations=["Calculated strictly by Python pandas; Group margins calculated as SUM(profit)/SUM(net_sales)*100."],
                )
            except Exception:
                grp = plan.group_column or "region"
                return op_compare_groups(df, grp, filters=plan.filters, source_info=src_info)

        # 6. Monthly Trend
        if op == "monthly_trend":
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                dt_col = mapping.get_col("date") or plan.target_column or "Order_Date"
                trend = FinancialMetricsEngine.compute_monthly_trend(df_fin, dt_col)

                month_filter = plan.time_range
                filtered_month = None
                if month_filter:
                    import calendar
                    m_lower = month_filter.lower()
                    for p in trend:
                        p_period = p["period"]  # "2024-03"
                        try:
                            month_num = int(p_period.split("-")[1])
                            cal_name = calendar.month_name[month_num].lower()
                            cal_abbr = calendar.month_abbr[month_num].lower()
                            if m_lower in cal_name or m_lower in cal_abbr or m_lower in p_period:
                                filtered_month = {
                                    "period": p["period"],
                                    "month_name": calendar.month_name[month_num],
                                    "value": p["net_sales"],
                                    "net_sales": p["net_sales"],
                                    "profit": p["profit"],
                                    "profit_margin_percentage": p["profit_margin_percentage"],
                                    "order_count": p["order_count"],
                                }
                                break
                        except Exception:
                            pass

                chart = {
                    "type": "line",
                    "title": "Monthly Revenue Trend",
                    "data": trend,
                    "x_key": "period",
                    "y_key": "net_sales",
                }

                return OperationResult(
                    operation="monthly_trend",
                    status="success",
                    values={
                        "periods": trend,
                        "filtered_month": filtered_month,
                        "trend": trend,
                    },
                    table_payload=trend,
                    chart_payload=chart,
                    source_references=[src_info],
                    limitations=["Calculated strictly by Python pandas."],
                )
            except Exception:
                dt = plan.target_column or "order_date"
                met = plan.metric_column or "revenue"
                return op_monthly_trend(df, dt, met, month_filter=plan.time_range, source_info=src_info)

        # 7. Other standard operations
        if op == "count":
            return op_count(df, plan.target_column, filters=plan.filters, source_info=src_info)

        elif op == "period_over_period_change":
            dt = plan.target_column or "order_date"
            met = plan.metric_column or "revenue"
            return op_period_over_period_change(df, dt, met, filters=plan.filters, source_info=src_info)

        elif op == "top_drivers_of_change":
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                dt = mapping.get_col("date") or plan.target_column or "order_date"
                dim = mapping.get_col("product") or mapping.get_col("category") or plan.group_column or "product_name"
                met = "calc_net_sales" if "calc_net_sales" in df_fin.columns else (mapping.get_col("net_sales") or "revenue")
                return op_top_drivers_of_change(df_fin, dt, dim, met, source_info=src_info)
            except Exception:
                dt = plan.target_column or "order_date"
                dim = plan.group_column or "product_name"
                met = plan.metric_column or "revenue"
                return op_top_drivers_of_change(df, dt, dim, met, source_info=src_info)

        elif op == "find_outliers":
            try:
                df_fin = FinancialMetricsEngine.compute_row_financials(df, mapping, filters=plan.filters)
                ident = mapping.get_col("order_id") or plan.target_column or "Order_ID"
                return op_find_outliers(df_fin, "calc_net_sales", id_col=ident, source_info=src_info)
            except Exception:
                met = plan.metric_column or "revenue"
                ident = plan.target_column or "order_id"
                return op_find_outliers(df, met, id_col=ident, source_info=src_info)

        elif op == "missing_values_report":
            return op_missing_values_report(df, source_info=src_info)

        elif op == "duplicate_report":
            return op_duplicate_report(df, source_info=src_info)

        elif op == "list_top_insights":
            insights = getattr(analysis, "insights", []) if analysis else []
            return op_list_top_insights(insights, n=plan.top_n or 3)

        elif op == "get_insight_evidence":
            insights = getattr(analysis, "insights", []) if analysis else []
            return op_get_insight_evidence(insights, insight_id=plan.insight_id)

        # Default fallback to total or count
        return op_total(df, "revenue" if "revenue" in df.columns else df.columns[0], source_info=src_info)

    @classmethod
    def determine_plan_heuristic(
        cls,
        question: str,
        df: pd.DataFrame,
        dataset: Optional[Any] = None,
        analysis: Optional[Any] = None,
    ) -> SafePlan:
        """
        Determines SafePlan deterministically when no LLM key is configured
        or as a guaranteed fallback. Uses IntentRouter and SchemaMapper.
        """
        from backend.app.analytics.schema_mapping import SchemaMapper
        from backend.app.llm.intent import IntentRouter

        mapping = SchemaMapper.map_dataframe(df)
        return IntentRouter.match_heuristic_plan(question, df, mapping)

    @classmethod
    def determine_plan(cls, question: str, metrics: Dict[str, Any]) -> str:
        """Legacy keyword mapper for backward compatibility with existing tests."""
        q = question.lower()
        if any(term in q for term in ["outlier", "anomaly", "abnormal", "unusual", "z-score", "spike"]):
            return "outliers"
        if any(term in q for term in ["trend", "growth", "month", "trajectory", "over time", "period", "timeline", "quarter"]):
            return "trend_growth"
        if any(term in q for term in ["product", "item", "best selling", "worst selling", "top product"]):
            return "top_products"
        if any(term in q for term in ["customer", "client", "buyer", "account"]):
            return "top_customers"
        if any(term in q for term in ["category", "breakdown", "segment", "region", "share", "proportion"]):
            return "category_breakdown"
        if any(term in q for term in ["revenue", "margin", "profit", "cost", "sales", "aov", "average order"]):
            return "revenue_margins"
        if any(term in q for term in ["missing", "quality", "duplicate", "clean", "error", "null", "invalid"]):
            return "data_quality"
        return "summary"

    @classmethod
    def execute_plan(
        cls,
        operation: str,
        metrics: Dict[str, Any],
        dataset_ids: List[str],
    ) -> Tuple[Dict[str, Any], List[str], List[str], Optional[str]]:
        """Legacy execution method against precomputed metrics dictionary."""
        sources = [f"dataset:{d}" for d in dataset_ids]
        limitations = [
            "Mathematical operations executed strictly by Python pandas.",
            "Historical factual data only; no synthetic extrapolations.",
        ]
        evidence: Dict[str, Any] = {}
        missing_warning: Optional[str] = None

        if operation == "revenue_margins":
            if "total_revenue" in metrics:
                evidence = {
                    "total_revenue": metrics["total_revenue"],
                    "gross_profit": metrics.get("gross_profit", 0.0),
                    "gross_margin_percentage": metrics.get("gross_margin_percentage", 0.0),
                    "average_order_value": metrics.get("average_order_value", 0.0),
                    "row_count": metrics.get("row_count", 0),
                }
            else:
                missing_warning = "This dataset does not contain revenue or pricing columns. Revenue analysis cannot be computed."

        elif operation == "top_products":
            if "top_products" in metrics and metrics["top_products"]:
                evidence = {
                    "top_products": metrics["top_products"],
                    "bottom_products": metrics.get("bottom_products", []),
                }
            else:
                missing_warning = "This dataset does not contain identifiable product name columns."

        elif operation == "top_customers":
            if "top_customers" in metrics and metrics["top_customers"]:
                evidence = {
                    "top_customers": metrics["top_customers"],
                    "bottom_customers": metrics.get("bottom_customers", []),
                }
            else:
                missing_warning = "This dataset does not contain identifiable customer ID columns."

        elif operation == "category_breakdown":
            if "category_breakdown" in metrics and metrics["category_breakdown"]:
                evidence = {
                    "category_breakdown": metrics["category_breakdown"],
                }
            else:
                missing_warning = "This dataset does not contain categorical segments or regions."

        elif operation == "trend_growth":
            if "time_series_growth" in metrics and metrics["time_series_growth"].get("periods"):
                ts = metrics["time_series_growth"]
                evidence = {
                    "overall_growth_rate": ts.get("overall_growth_rate"),
                    "trend_direction": ts.get("trend_direction"),
                    "periods": ts.get("periods", []),
                }
            else:
                missing_warning = "This dataset does not contain sequential date/timestamp columns required for time-series trend analysis."

        elif operation == "outliers":
            if "revenue_outliers" in metrics and metrics["revenue_outliers"]:
                evidence = {
                    "revenue_outliers": metrics["revenue_outliers"],
                }
            else:
                evidence = {
                    "revenue_outliers": [],
                    "message": "No statistical outliers exceeding 2.0 standard deviations were found.",
                }

        elif operation == "data_quality":
            evidence = {
                "row_count": metrics.get("row_count", 0),
                "column_count": metrics.get("column_count", 0),
                "descriptive_stats": metrics.get("descriptive_stats", {}),
            }

        else:  # summary default
            evidence = {
                "row_count": metrics.get("row_count", 0),
                "column_count": metrics.get("column_count", 0),
                "total_revenue": metrics.get("total_revenue"),
                "gross_profit": metrics.get("gross_profit"),
                "gross_margin_percentage": metrics.get("gross_margin_percentage"),
                "average_order_value": metrics.get("average_order_value"),
            }
            evidence = {k: v for k, v in evidence.items() if v is not None}

        return evidence, sources, limitations, missing_warning


