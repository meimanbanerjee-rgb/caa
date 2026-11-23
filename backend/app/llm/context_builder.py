# backend/app/llm/context_builder.py
# Constructs lightweight dataset context (schema, meanings, category samples) for safe LLM planning.

from typing import Any, Dict, List, Optional
import pandas as pd
from backend.app.models.dataset import DatasetModel


class ContextBuilder:
    """Extracts column metadata and category samples without sending full rows."""

    @classmethod
    def build_planning_context(
        cls,
        df: pd.DataFrame,
        dataset: Optional[DatasetModel] = None,
    ) -> Dict[str, Any]:
        """
        Builds a compact context dictionary containing:
        - filename, row_count, column_count
        - columns with detected type, semantic meaning, and top distinct values (if category/text)
        """
        col_metadata: List[Dict[str, Any]] = []

        # Map semantic meanings from dataset profile if available
        meaning_map: Dict[str, str] = {}
        if dataset and dataset.tables:
            for t in dataset.tables:
                for c in t.columns:
                    if c.suggested_meaning:
                        meaning_map[c.name] = c.suggested_meaning

        for col in df.columns:
            series = df[col]
            dtype_str = str(series.dtype)

            # Determine simplified type
            if pd.api.types.is_numeric_dtype(series):
                simp_type = "number"
                samples = []
            elif pd.api.types.is_datetime64_any_dtype(series):
                simp_type = "date"
                samples = []
            else:
                # Check if it could be a date string
                simp_type = "category" if series.nunique() <= 50 else "text"
                # Sample distinct non-null values
                samples = [str(x) for x in series.dropna().unique()[:4].tolist()]

            col_metadata.append({
                "column_name": str(col),
                "type": simp_type,
                "meaning": meaning_map.get(str(col), ""),
                "sample_values": samples,
            })

        return {
            "filename": dataset.filename if dataset else "dataset",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": col_metadata,
        }

    @classmethod
    def format_planning_prompt(cls, context: Dict[str, Any], question: str) -> str:
        """Formats the prompt instructing the LLM to choose a validated SafePlan."""
        cols_text = "\n".join(
            f"- `{c['column_name']}` ({c['type']}{', meaning: ' + c['meaning'] if c['meaning'] else ''}"
            f"{', sample values: ' + str(c['sample_values']) if c['sample_values'] else ''})"
            for c in context["columns"]
        )

        return (
            f"User Question: \"{question}\"\n\n"
            f"Dataset: {context['filename']} ({context['row_count']} rows, {context['column_count']} columns)\n"
            f"Available Columns:\n{cols_text}\n\n"
            "INSTRUCTIONS:\n"
            "Select the single best operation from the ALLOWED OPERATIONS list:\n"
            "['total', 'average', 'count', 'group_by_sum', 'top_n', 'bottom_n', 'compare_groups', "
            "'period_over_period_change', 'monthly_trend', 'top_drivers_of_change', 'find_outliers', "
            "'missing_values_report', 'duplicate_report', 'list_top_insights', 'get_insight_evidence']\n\n"
            "CRITICAL: If the question asks for external info not in the dataset (e.g. weather, sports, unrelated topics), "
            "set operation to 'unanswerable' with missing_fields listing the missing concept.\n\n"
            "Respond ONLY with a JSON object following this exact structure (no markdown, no other text):\n"
            "{\n"
            '  "operation": "<operation_name>",\n'
            '  "target_column": "<column_name_or_null>",\n'
            '  "group_column": "<group_column_name_or_null>",\n'
            '  "metric_column": "<metric_column_name_or_null>",\n'
            '  "top_n": 5,\n'
            '  "filters": {},\n'
            '  "time_range": null\n'
            "}"
        )

