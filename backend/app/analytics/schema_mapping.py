# backend/app/analytics/schema_mapping.py
# Maps dataset columns to canonical business roles using synonym matching and type checks.
# Detects discount formats (decimal, percentage, strings with %) and missing required roles.

from typing import Any, Dict, List, Optional, Set
import re
import pandas as pd
from pydantic import BaseModel, Field


class RoleMapping(BaseModel):
    """Maps a canonical business role to an actual column name with confidence."""
    role: str
    column_name: str
    confidence: float = 1.0  # 1.0 for exact/synonym match, 0.7 for substring
    status: str = "confirmed"  # 'confirmed', 'suggested', 'missing'


class SchemaMapping(BaseModel):
    """Complete schema mapping of a dataset's columns to canonical business roles."""
    roles: Dict[str, RoleMapping] = Field(default_factory=dict)
    unmapped_columns: List[str] = Field(default_factory=list)
    discount_format: Optional[str] = None  # 'decimal_rate', 'percentage_int', 'percentage_str'

    def get_col(self, role: str) -> Optional[str]:
        """Returns the actual column name for a given canonical role if present."""
        if role in self.roles:
            return self.roles[role].column_name
        return None

    def has_role(self, role: str) -> bool:
        """Checks if a canonical role is mapped."""
        return role in self.roles

    def get_missing_roles(self, required_roles: List[str]) -> List[str]:
        """Returns a list of roles that are missing from the mapping."""
        return [r for r in required_roles if not self.has_role(r)]


SYNONYM_DICTIONARY: Dict[str, List[str]] = {
    "quantity": [
        "quantity", "qty", "units", "units_sold", "volume", "order_quantity",
        "item_quantity", "number_of_units", "count"
    ],
    "unit_price": [
        "unit_price", "unitprice", "price", "selling_price", "rate",
        "item_price", "retail_price", "price_per_unit"
    ],
    "unit_cost": [
        "unit_cost", "unitcost", "cost_per_unit", "item_cost", "cogs_per_unit",
        "purchase_price", "manufacturing_cost"
    ],
    "discount": [
        "discount", "discount_rate", "discount_pct", "discount_percent",
        "discount_percentage", "rebate", "discount_amount"
    ],
    "gross_sales": [
        "gross_sales", "gross_revenue", "gross_amount", "gross_total"
    ],
    "net_sales": [
        "net_sales", "net_revenue", "sales", "revenue", "total_sales",
        "total_revenue", "turnover", "billed_amount", "total_amount"
    ],
    "total_cost": [
        "total_cost", "cogs", "cost", "total_cogs", "expenses",
        "expense", "total_expense"
    ],
    "profit": [
        "profit", "net_profit", "gross_profit", "margin", "margin_amount",
        "net_margin", "operating_profit", "earnings"
    ],
    "product": [
        "product", "product_name", "item", "item_name", "sku", "product_title",
        "description", "article", "product_description"
    ],
    "category": [
        "category", "product_category", "department", "segment", "class",
        "product_line", "product_group"
    ],
    "region": [
        "region", "territory", "area", "zone", "location", "country",
        "state", "city", "market", "district"
    ],
    "marketing_channel": [
        "marketing_channel", "channel", "acquisition_channel", "medium",
        "source", "campaign_source", "traffic_channel"
    ],
    "customer": [
        "customer_id", "customer", "customer_name", "cust_id", "client_id",
        "client", "user_id", "buyer_id", "account_id"
    ],
    "order_id": [
        "order_id", "order_number", "transaction_id", "invoice_id",
        "invoice_number", "order_no", "trans_id"
    ],
    "date": [
        "order_date", "date", "transaction_date", "invoice_date",
        "timestamp", "created_at", "purchase_date", "sale_date"
    ],
    "status": [
        "payment_status", "order_status", "status", "payment_state", "state"
    ],
}


class SchemaMapper:
    """Infers canonical roles from column names and value inspections."""

    @classmethod
    def clean_token(cls, name: str) -> str:
        """Converts column name into clean snake_case string."""
        return re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")

    @classmethod
    def detect_discount_format(cls, series: pd.Series) -> str:
        """
        Detects discount format:
        - 'percentage_str': e.g. "10%", "5%"
        - 'percentage_int': numeric with values > 1.0 (e.g. 10.0 for 10%)
        - 'decimal_rate': numeric with values <= 1.0 (e.g. 0.10 for 10%)
        """
        non_null = series.dropna().astype(str).str.strip()
        if non_null.empty:
            return "decimal_rate"

        if non_null.str.contains("%").any():
            return "percentage_str"

        num_series = pd.to_numeric(series, errors="coerce").dropna()
        if num_series.empty:
            return "decimal_rate"

        max_val = num_series.max()
        if max_val > 1.0:
            return "percentage_int"
        return "decimal_rate"

    @classmethod
    def parse_discount_rate(cls, series: pd.Series, format_type: Optional[str] = None) -> pd.Series:
        """Parses any discount column into a clean decimal rate series [0.0, 1.0]."""
        if format_type is None:
            format_type = cls.detect_discount_format(series)

        if format_type == "percentage_str":
            cleaned = series.astype(str).str.replace("%", "", regex=False).str.strip()
            num = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
            return (num / 100.0).clip(lower=0.0, upper=1.0)
        elif format_type == "percentage_int":
            num = pd.to_numeric(series, errors="coerce").fillna(0.0)
            return (num / 100.0).clip(lower=0.0, upper=1.0)
        else:
            num = pd.to_numeric(series, errors="coerce").fillna(0.0)
            return num.clip(lower=0.0, upper=1.0)

    @classmethod
    def map_dataframe(cls, df: pd.DataFrame) -> SchemaMapping:
        """Maps all DataFrame columns to canonical roles."""
        mapping = SchemaMapping()
        mapped_cols: Set[str] = set()

        # Priority 1: Exact and synonym token matching
        for role, synonyms in SYNONYM_DICTIONARY.items():
            if role in mapping.roles:
                continue

            for col in df.columns:
                if col in mapped_cols:
                    continue

                col_clean = cls.clean_token(str(col))

                # Exact match against synonym
                if col_clean in synonyms:
                    mapping.roles[role] = RoleMapping(
                        role=role,
                        column_name=str(col),
                        confidence=1.0,
                        status="confirmed",
                    )
                    mapped_cols.add(str(col))
                    break

        # Priority 2: Substring matching for unmapped roles
        for role, synonyms in SYNONYM_DICTIONARY.items():
            if role in mapping.roles:
                continue

            for col in df.columns:
                if col in mapped_cols:
                    continue

                col_clean = cls.clean_token(str(col))
                # Substring check with word boundaries or matching token
                tokens = set(col_clean.split("_"))
                if any(syn in tokens for syn in synonyms):
                    mapping.roles[role] = RoleMapping(
                        role=role,
                        column_name=str(col),
                        confidence=0.85,
                        status="confirmed",
                    )
                    mapped_cols.add(str(col))
                    break

        # Check discount format if discount column mapped
        if "discount" in mapping.roles:
            disc_col = mapping.roles["discount"].column_name
            mapping.discount_format = cls.detect_discount_format(df[disc_col])

        # Track unmapped columns
        mapping.unmapped_columns = [str(c) for c in df.columns if str(c) not in mapped_cols]
        return mapping

