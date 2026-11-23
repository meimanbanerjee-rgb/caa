# backend/app/ingestion/excel_parser.py
# Safe multi-sheet Excel (.xlsx) parser reading values only with data_only=True (FR-2, FR-4).

from pathlib import Path
from typing import Any, Dict, List, Tuple
import uuid
import openpyxl
import pandas as pd
import numpy as np

from backend.app.models.dataset import TableModel, ColumnProfile, ColumnQualityStats


class ExcelParser:
    """Parses Excel workbooks extracting multiple sheets safely without executing macros or formulas."""

    @classmethod
    def parse(
        cls,
        file_path: Path,
        dataset_id: str,
    ) -> Tuple[List[TableModel], List[str]]:
        """
        Parses all non-empty sheets in an Excel workbook.
        Uses data_only=True to ensure no VBA macros or malicious formulas are executed.
        """
        tables: List[TableModel] = []
        warnings: List[str] = []

        try:
            # openpyxl with data_only=True extracts pre-calculated values and ignores formula code
            wb = openpyxl.load_workbook(
                filename=str(file_path),
                read_only=True,
                data_only=True,
                keep_vba=False,
            )
        except Exception as e:
            raise ValueError(f"Corrupted or invalid Excel file: {str(e)}") from e

        sheet_names = wb.sheetnames
        if not sheet_names:
            warnings.append(f"Excel workbook '{file_path.name}' contains no visible sheets.")
            wb.close()
            return tables, warnings

        for sheet_name in sheet_names:
            sheet = wb[sheet_name]
            rows_iter = sheet.iter_rows(values_only=True)
            
            # Extract header row
            try:
                header_row = next(rows_iter, None)
            except Exception:
                header_row = None

            if not header_row or all(cell is None for cell in header_row):
                warnings.append(f"Sheet '{sheet_name}' is empty and was skipped.")
                continue

            # Clean and deduplicate headers
            headers: List[str] = []
            seen: Dict[str, int] = {}
            for idx, cell in enumerate(header_row):
                col_name = str(cell).strip() if cell is not None else f"column_{idx + 1}"
                if not col_name:
                    col_name = f"column_{idx + 1}"
                if col_name in seen:
                    seen[col_name] += 1
                    col_name = f"{col_name}_{seen[col_name]}"
                else:
                    seen[col_name] = 0
                headers.append(col_name)

            # Collect raw data rows
            raw_data = []
            for row in rows_iter:
                # Skip entirely blank rows
                if all(c is None for c in row):
                    continue
                # Align row length with headers
                padded = list(row[: len(headers)])
                if len(padded) < len(headers):
                    padded.extend([None] * (len(headers) - len(padded)))
                raw_data.append(padded)

            if not raw_data:
                warnings.append(f"Sheet '{sheet_name}' has headers but no data rows.")
                continue

            # Convert to DataFrame for standard profiling
            df = pd.DataFrame(raw_data, columns=headers)

            columns_profile: List[ColumnProfile] = []
            for col in df.columns:
                series = df[col]
                null_count = int(series.isna().sum())
                total_count = len(series)
                null_pct = round((null_count / total_count * 100), 1) if total_count > 0 else 0.0
                distinct_count = int(series.nunique(dropna=True))

                detected_type = "text"
                if pd.api.types.is_numeric_dtype(series):
                    detected_type = "number"
                elif pd.api.types.is_datetime64_any_dtype(series):
                    detected_type = "date"
                elif distinct_count < 25 and distinct_count < (total_count * 0.5):
                    detected_type = "category"
                elif "id" in col.lower() or "code" in col.lower():
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

            # Sample rows preview
            sample_df = df.head(15).replace({np.nan: None})
            sample_rows = sample_df.to_dict(orient="records")

            table = TableModel(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                name=sheet_name,
                row_count=int(len(df)),
                column_count=int(len(df.columns)),
                columns=columns_profile,
                sample_rows=sample_rows,
            )
            tables.append(table)

        wb.close()
        return tables, warnings
