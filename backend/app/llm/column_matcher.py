# backend/app/llm/column_matcher.py
# Resolves user concepts (e.g. 'revenue', 'profit', 'region') to exact dataset column names.

import difflib
from typing import Dict, List, Optional, Tuple
import pandas as pd


# Canonical synonyms and semantic mappings
SYNONYMS: Dict[str, List[str]] = {
    "revenue": ["revenue", "sales", "turnover", "gross_sales", "total_sales", "income", "amount"],
    "profit": ["profit", "margin", "gross_profit", "net_profit", "net_income", "earnings"],
    "cost": ["cost", "unit_cost", "expenses", "expense", "cogs", "spending"],
    "region": ["region", "area", "territory", "location", "zone", "geography", "country", "state", "city"],
    "category": ["category", "segment", "department", "type", "group", "class"],
    "product": ["product_name", "product", "item", "sku", "product_title", "description"],
    "customer": ["customer_id", "customer", "client", "buyer", "account", "customer_name"],
    "date": ["order_date", "date", "timestamp", "transaction_date", "day", "month", "created_at"],
    "units": ["units_sold", "units", "quantity", "qty", "volume", "count"],
}


class ColumnMatcher:
    """
    Fuzzy and semantic matcher that maps target concepts to verified DataFrame columns.
    If matching is uncertain or ambiguous, returns clarification details.
    """

    @classmethod
    def match_column(
        cls,
        target_concept: str,
        df_columns: List[str],
        semantic_meanings: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[str], bool, List[str]]:
        """
        Attempts to match target_concept to a column in df_columns.
        Returns: (matched_column_or_None, is_ambiguous, candidate_columns)
        """
        if not target_concept or not df_columns:
            return None, False, []

        clean_concept = target_concept.lower().strip().replace(" ", "_")
        col_map = {c.lower().strip().replace(" ", "_"): c for c in df_columns}

        # 1. Exact match
        if clean_concept in col_map:
            return col_map[clean_concept], False, []

        # 2. Check confirmed / suggested semantic meanings
        if semantic_meanings:
            for sem_key, col_name in semantic_meanings.items():
                if sem_key.lower() == clean_concept and col_name in df_columns:
                    return col_name, False, []

        # 3. Synonym mapping
        candidate_synonyms = SYNONYMS.get(clean_concept, [])
        matched_candidates = []
        for syn in candidate_synonyms:
            for clean_col, orig_col in col_map.items():
                if syn == clean_col or syn in clean_col or clean_col in syn:
                    if orig_col not in matched_candidates:
                        matched_candidates.append(orig_col)

        if len(matched_candidates) == 1:
            return matched_candidates[0], False, []
        elif len(matched_candidates) > 1:
            # Ambiguous match among multiple matching columns
            return None, True, matched_candidates

        # 4. Fuzzy string match
        close_matches = difflib.get_close_matches(clean_concept, list(col_map.keys()), n=2, cutoff=0.7)
        if len(close_matches) == 1:
            return col_map[close_matches[0]], False, []
        elif len(close_matches) > 1:
            return None, True, [col_map[m] for m in close_matches]

        return None, False, []

    @classmethod
    def find_best_numeric_column(cls, df: pd.DataFrame, concept: str = "revenue") -> Optional[str]:
        """Finds the most appropriate numeric column for monetary or metric aggregation."""
        col, ambiguous, _ = cls.match_column(concept, list(df.columns))
        if col and pd.api.types.is_numeric_dtype(df[col]):
            return col

        # Fallback to first numeric column
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        return numeric_cols[0] if numeric_cols else None

