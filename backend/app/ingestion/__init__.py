# backend/app/ingestion/__init__.py
# Unified dispatcher coordinating validation and specialized file parsers (CSV, Excel, JSON, PDF).

from pathlib import Path
from typing import List, Tuple
from backend.app.models.dataset import TableModel
from backend.app.ingestion.validator import validate_file_metadata, sanitize_filename
from backend.app.ingestion.csv_parser import CsvParser
from backend.app.ingestion.excel_parser import ExcelParser
from backend.app.ingestion.json_parser import JsonParser
from backend.app.ingestion.pdf_parser import PdfParser


def parse_uploaded_file(
    file_path: Path,
    original_filename: str,
    dataset_id: str,
) -> Tuple[List[TableModel], List[str]]:
    """
    Routes an uploaded file to its appropriate parser based on file extension.
    Returns: (list_of_tables, list_of_warnings)
    Raises: ValueError with a friendly error message if file cannot be parsed or is corrupted.
    """
    clean_name = sanitize_filename(original_filename)
    ext = Path(clean_name).suffix.lower()
    tables: List[TableModel] = []
    warnings: List[str] = []

    if ext in [".csv", ".tsv", ".txt"]:
        table, warn = CsvParser.parse(file_path, dataset_id=dataset_id, table_name="Main Table")
        tables.append(table)
        warnings.extend(warn)

    elif ext == ".xlsx":
        sheet_tables, warn = ExcelParser.parse(file_path, dataset_id=dataset_id)
        tables.extend(sheet_tables)
        warnings.extend(warn)

    elif ext in [".json", ".jsonl"]:
        table, warn = JsonParser.parse(file_path, dataset_id=dataset_id)
        tables.append(table)
        warnings.extend(warn)

    elif ext == ".pdf":
        pdf_tables, warn = PdfParser.parse(file_path, dataset_id=dataset_id)
        tables.extend(pdf_tables)
        warnings.extend(warn)

    else:
        raise ValueError(f"Unsupported file type '{ext}' for file '{original_filename}'.")

    return tables, warnings
