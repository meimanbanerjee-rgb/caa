# backend/app/ingestion/csv_parser.py
# Safe CSV and TSV file parser with encoding fallback and delimiter sniffing (FR-1, FR-2, FR-5).

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import io
import uuid
import pandas as pd
import numpy as np

from backend.app.models.dataset import TableModel, ColumnProfile, ColumnQualityStats


class CsvParser:
    """Safely extracts tabular data from CSV and TSV files with encoding resilience."""

    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    @classmethod
    def detect_encoding_and_delimiter(cls, file_path: Path) -> Tuple[str, str]:
        """Detects functional encoding and sniffs column delimiter."""
        detected_encoding = "utf-8"
        sample_bytes = b""

        with open(file_path, "rb") as f:
            sample_bytes = f.read(8192)

        for enc in cls.SUPPORTED_ENCODINGS:
            try:
                sample_text = sample_bytes.decode(enc)
                detected_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        # Sniff delimiter
        delimiter = ","
        if file_path.suffix.lower() == ".tsv":
            delimiter = "\t"
        else:
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text)
                if dialect.delimiter in [",", "\t", ";", "|"]:
                    delimiter = dialect.delimiter
            except Exception:
                delimiter = ","

        return detected_encoding, delimiter

    @classmethod
    def parse(
        cls,
        file_path: Path,
        dataset_id: str,
        table_name: str = "Main Table",
    ) -> Tuple[TableModel, List[str]]:
        """
        Parses a CSV/TSV into a TableModel, tracking all skipped data or anomalies as warnings.
        """
        warnings: List[str] = []
        encoding, delimiter = cls.detect_encoding_and_delimiter(file_path)

        try:
            # Read CSV with pandas, treating all formulas as raw text
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=delimiter,
                on_bad_lines="warn",
                low_memory=False,
            )
        except Exception as e:
            raise ValueError(f"Could not parse CSV file: {str(e)}") from e

        if df.empty:
            warnings.append(f"The CSV file '{file_path.name}' contains no data rows.")
            return (
                TableModel(
                    id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    name=table_name,
                    row_count=0,
                    column_count=0,
                    columns=[],
                    sample_rows=[],
                ),
                warnings,
            )

        # Sanitize column names: remove leading/trailing whitespace and ensure unique names
        original_cols = list(df.columns)
        clean_cols = []
        seen = {}
        for col in original_cols:
            col_str = str(col).strip()
            if not col_str or col_str.lower().startswith("unnamed:"):
                col_str = f"column_{len(clean_cols) + 1}"
            if col_str in seen:
                seen[col_str] += 1
                unique_name = f"{col_str}_{seen[col_str]}"
                warnings.append(f"Duplicate column header '{col_str}' renamed to '{unique_name}'")
                col_str = unique_name
            else:
                seen[col_str] = 0
            clean_cols.append(col_str)

        df.columns = clean_cols

        # Profile basic column shapes
        columns_profile: List[ColumnProfile] = []
        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            total_count = len(series)
            null_pct = round((null_count / total_count * 100), 1) if total_count > 0 else 0.0
            distinct_count = int(series.nunique(dropna=True))

            # Inferred preliminary data type
            detected_type = "text"
            if pd.api.types.is_numeric_dtype(series):
                detected_type = "number"
            elif pd.api.types.is_datetime64_any_dtype(series):
                detected_type = "date"
            elif distinct_count < 25 and distinct_count < (total_count * 0.5):
                detected_type = "category"
            elif "id" in col.lower() or "key" in col.lower() or "code" in col.lower():
                detected_type = "id"

            stats = ColumnQualityStats(
                null_count=null_count,
                null_percentage=null_pct,
                distinct_count=distinct_count,
                duplicate_count=int(total_count - distinct_count - null_count),
                warnings=[],
            )

            columns_profile.append(
                ColumnProfile(
                    name=col,
                    detected_type=detected_type,
                    suggested_meaning=None,
                    meaning_status="suggested",
                    quality_stats=stats,
                )
            )

        # Convert sample rows safely (handling NaN -> None)
        sample_df = df.head(15).replace({np.nan: None})
        sample_rows = sample_df.to_dict(orient="records")

        table = TableModel(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            name=table_name,
            row_count=int(len(df)),
            column_count=int(len(df.columns)),
            columns=columns_profile,
            sample_rows=sample_rows,
        )

        return table, warnings
