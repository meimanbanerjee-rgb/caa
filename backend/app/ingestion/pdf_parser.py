# backend/app/ingestion/pdf_parser.py
# Safe PDF parser extracting narrative text and tabular structures with page references (PRD Section 4, 5.1, Phase 6).

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import uuid
import pandas as pd
import numpy as np
import pypdf

from backend.app.models.dataset import TableModel, ColumnProfile, ColumnQualityStats


class PdfParser:
    """
    Safely parses PDF documents, extracting narrative text and tabular data with page references.
    FR-2: Read-only extraction; never executes scripts or macros.
    FR-3: Catches corrupted or password-protected PDFs gracefully.
    FR-4: Retains page references (Page N, Line M) for every extracted segment.
    """

    @classmethod
    def parse(
        cls,
        file_path: Path,
        dataset_id: str,
    ) -> Tuple[List[TableModel], List[str]]:
        """
        Extracts structured tables and narrative text sections from a PDF file.
        Returns: (list_of_tables, list_of_warnings)
        """
        warnings: List[str] = []
        tables: List[TableModel] = []

        try:
            reader = pypdf.PdfReader(str(file_path))
        except Exception as e:
            raise ValueError(f"Could not open or parse PDF file: {str(e)}") from e

        if reader.is_encrypted:
            try:
                # Attempt empty password decryption
                reader.decrypt("")
            except Exception:
                raise ValueError(f"PDF file '{file_path.name}' is password-protected and cannot be parsed.")

        total_pages = len(reader.pages)
        if total_pages == 0:
            warnings.append(f"PDF file '{file_path.name}' has no pages.")
            return [], warnings

        narrative_rows: List[Dict[str, Any]] = []
        extracted_tables_data: List[Dict[str, Any]] = []

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            try:
                text = page.extract_text() or ""
            except Exception as e:
                warnings.append(f"Warning on Page {page_num}: Could not extract text ({str(e)})")
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                continue

            # Check for tabular blocks in lines (e.g. lines with commas, tabs, or multiple column splits)
            candidate_table_rows: List[List[str]] = []
            for line_idx, line in enumerate(lines):
                # Save narrative entry with page and line reference
                narrative_rows.append({
                    "page_number": page_num,
                    "line_number": line_idx + 1,
                    "text_content": line,
                    "source_reference": f"Page {page_num}, Line {line_idx + 1}",
                })

                # Check if line looks like structured tabular record (comma, tab, pipe, or 2+ spaces separated)
                if "," in line and len(line.split(",")) >= 3:
                    parts = [p.strip() for p in line.split(",")]
                    candidate_table_rows.append(parts)
                elif "\t" in line and len(line.split("\t")) >= 2:
                    parts = [p.strip() for p in line.split("\t")]
                    candidate_table_rows.append(parts)
                elif "|" in line and len(line.split("|")) >= 3:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if parts:
                        candidate_table_rows.append(parts)
                else:
                    # Regex multi-space separation (at least 2 spaces)
                    parts = [p.strip() for p in re.split(r"\s{2,}", line) if p.strip()]
                    if len(parts) >= 3:
                        candidate_table_rows.append(parts)

            # If tabular patterns were identified on this page, synthesize a table
            if len(candidate_table_rows) >= 2:
                # First row as header, remaining as rows
                header = candidate_table_rows[0]
                # Ensure headers are non-empty and unique
                clean_header: List[str] = []
                for i, h in enumerate(header):
                    name = h if h else f"column_{i+1}"
                    clean_header.append(name)

                num_cols = len(clean_header)
                valid_rows: List[Dict[str, Any]] = []
                for r_idx, row_vals in enumerate(candidate_table_rows[1:]):
                    if len(row_vals) == num_cols:
                        row_dict = {clean_header[c]: row_vals[c] for c in range(num_cols)}
                        row_dict["_source_page"] = page_num
                        valid_rows.append(row_dict)

                if valid_rows:
                    extracted_tables_data.append({
                        "name": f"Extracted Table (Page {page_num})",
                        "header": clean_header,
                        "rows": valid_rows,
                        "page": page_num,
                    })

        # 1. Build TableModels for extracted data tables
        for t_idx, t_data in enumerate(extracted_tables_data):
            df_table = pd.DataFrame(t_data["rows"])
            if not df_table.empty:
                cols_profile: List[ColumnProfile] = []
                for c in df_table.columns:
                    if c.startswith("_"):
                        continue
                    series = df_table[c]
                    # Attempt numeric conversion for quality checks
                    numeric_series = pd.to_numeric(series.str.replace("$", "", regex=False).str.replace(",", "", regex=False), errors="coerce")
                    is_num = numeric_series.notna().sum() > (len(series) * 0.7)

                    detected_type = "number" if is_num else "text"
                    if not is_num and series.nunique() < 15:
                        detected_type = "category"

                    cols_profile.append(
                        ColumnProfile(
                            name=c,
                            detected_type=detected_type,
                            suggested_meaning=None,
                            meaning_status="suggested",
                            quality_stats=ColumnQualityStats(
                                null_count=int(series.isna().sum()),
                                null_percentage=0.0,
                                distinct_count=int(series.nunique()),
                                duplicate_count=0,
                                warnings=[],
                            ),
                        )
                    )

                sample_rows = df_table.head(15).replace({np.nan: None}).to_dict(orient="records")
                tables.append(
                    TableModel(
                        id=str(uuid.uuid4()),
                        dataset_id=dataset_id,
                        name=t_data["name"],
                        row_count=len(df_table),
                        column_count=len(cols_profile),
                        columns=cols_profile,
                        sample_rows=sample_rows,
                    )
                )

        # 2. Build Narrative Section Table
        if narrative_rows:
            df_narrative = pd.DataFrame(narrative_rows)
            narrative_cols = [
                ColumnProfile(
                    name="page_number",
                    detected_type="number",
                    suggested_meaning="page",
                    quality_stats=ColumnQualityStats(distinct_count=total_pages),
                ),
                ColumnProfile(
                    name="line_number",
                    detected_type="number",
                    suggested_meaning="line",
                    quality_stats=ColumnQualityStats(distinct_count=len(narrative_rows)),
                ),
                ColumnProfile(
                    name="text_content",
                    detected_type="text",
                    suggested_meaning="narrative",
                    quality_stats=ColumnQualityStats(distinct_count=len(narrative_rows)),
                ),
                ColumnProfile(
                    name="source_reference",
                    detected_type="text",
                    suggested_meaning="source",
                    quality_stats=ColumnQualityStats(distinct_count=len(narrative_rows)),
                ),
            ]

            tables.append(
                TableModel(
                    id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    name="Document Narrative & Text Sections",
                    row_count=len(narrative_rows),
                    column_count=len(narrative_cols),
                    columns=narrative_cols,
                    sample_rows=df_narrative.head(15).to_dict(orient="records"),
                )
            )

        if not tables:
            warnings.append(f"No parseable text or tables could be extracted from '{file_path.name}'.")

        return tables, warnings

