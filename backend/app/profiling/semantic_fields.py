# backend/app/profiling/semantic_fields.py
# Inferred semantic field mappings and domain classification (FR-8, FR-11).

from typing import Dict, List, Optional
import re
import pandas as pd


class SemanticFieldInferrer:
    """Infers business roles of columns and identifies the likely business domain."""

    SEMANTIC_PATTERNS: Dict[str, List[str]] = {
        "revenue": ["revenue", "sales", "total_amount", "turnover", "total_price", "grand_total", "billed_amount"],
        "cost": ["cost", "unit_cost", "cogs", "purchase_price", "expense", "manufacturing_cost"],
        "margin": ["margin", "profit", "gross_margin", "net_profit", "markup"],
        "units_sold": ["units_sold", "units", "quantity", "qty", "volume", "sold_qty", "order_quantity"],
        "unit_price": ["unit_price", "price", "rate", "selling_price", "retail_price"],
        "order_date": ["order_date", "date", "timestamp", "transaction_date", "invoice_date", "created_at"],
        "customer_id": ["customer_id", "cust_id", "client_id", "user_id", "buyer_id", "account_id"],
        "product_name": ["product_name", "product", "item_name", "item", "sku", "description", "title"],
        "category": ["category", "product_category", "department", "segment", "class", "product_line"],
        "region": ["region", "territory", "state", "city", "country", "location", "area", "zone"],
    }

    @classmethod
    def infer_meaning(cls, column_name: str, detected_type: str) -> Optional[str]:
        """
        Suggests a semantic business meaning based on column name tokens and type.
        Returns suggested role, or None if no high-confidence role matches.
        """
        col_clean = re.sub(r"[^a-zA-Z0-9]", "_", column_name.lower().strip())
        tokens = set(col_clean.split("_"))

        for meaning, keywords in cls.SEMANTIC_PATTERNS.items():
            for kw in keywords:
                if kw in col_clean or kw in tokens:
                    # Type sanity filter
                    if meaning in ["revenue", "cost", "margin", "units_sold", "unit_price"] and detected_type == "text":
                        continue
                    if meaning == "order_date" and detected_type not in ["date", "text"]:
                        continue
                    return meaning

        # Fallback keyword checks
        if "id" in tokens and detected_type == "id":
            return "customer_id" if "cust" in col_clean or "user" in col_clean else "identifier"

        return None

    @classmethod
    def guess_domain(cls, column_names: List[str]) -> str:
        """
        Guesses business domain based on set of available attributes (FR-11).
        Options: 'ecommerce', 'retail', 'saas', 'logistics', 'general'.
        """
        cols_text = " ".join(c.lower() for c in column_names)

        if any(w in cols_text for w in ["mrr", "arr", "churn", "subscription", "plan", "seats"]):
            return "saas"
        if any(w in cols_text for w in ["shipping", "warehouse", "tracking", "freight", "delivery", "inventory"]):
            return "logistics"
        if any(w in cols_text for w in ["product", "sku", "units", "sold", "margin", "retail"]):
            return "retail"
        if any(w in cols_text for w in ["cart", "checkout", "store", "order", "revenue"]):
            return "ecommerce"

        return "general_business"
