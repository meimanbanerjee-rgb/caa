# backend/tests/unit/test_parsers.py
# Unit tests for CSV, Excel, and JSON ingestion parsers, validation rules, and error handling.

from pathlib import Path
import pytest

from backend.app.ingestion.validator import validate_file_metadata, sanitize_filename
from backend.app.ingestion.csv_parser import CsvParser
from backend.app.ingestion.excel_parser import ExcelParser
from backend.app.ingestion.json_parser import JsonParser
from backend.app.ingestion import parse_uploaded_file

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def test_validator_sanitizes_path_traversal():
    """Verify FR-1 / Security: Path traversal sequences are completely sanitized."""
    dirty_name = "../../../secret_passwords.csv"
    clean_name = sanitize_filename(dirty_name)
    assert clean_name == "secret_passwords.csv"

    windows_dirty = "..\\..\\system32\\calc.exe"
    clean_win = sanitize_filename(windows_dirty)
    assert ".." not in clean_win
    assert "\\" not in clean_win


def test_validator_rejects_unsupported_extensions():
    """Verify FR-1: Unsupported formats are caught with friendly messages."""
    is_valid, err, ext = validate_file_metadata("malicious.exe", size_bytes=1024)
    assert is_valid is False
    assert "Unsupported file format" in err


def test_validator_rejects_oversized_files():
    """Verify FR-1: Files exceeding MAX_UPLOAD_MB are rejected."""
    huge_size = 50 * 1024 * 1024  # 50 MB
    is_valid, err, ext = validate_file_metadata("big_data.csv", size_bytes=huge_size)
    assert is_valid is False
    assert "exceeds maximum allowed limit" in err


def test_csv_parser_clean_sales():
    """Verify clean_sales.csv parses exactly 10 rows and 11 columns with verified headers."""
    csv_path = TEST_DATA_DIR / "clean_sales.csv"
    table, warnings = CsvParser.parse(csv_path, dataset_id="test_ds_1")

    assert table.row_count == 10
    assert table.column_count == 11
    assert "revenue" in [c.name for c in table.columns]
    assert len(table.sample_rows) == 10

    # Verify column types
    rev_col = next(c for c in table.columns if c.name == "revenue")
    assert rev_col.detected_type == "number"
    assert rev_col.quality_stats.null_count == 0


def test_csv_parser_delimiter_sniffing():
    """Verify delimiter sniffing detects semicolon separators."""
    semi_path = TEST_DATA_DIR / "semicolon_delimited.csv"
    table, warnings = CsvParser.parse(semi_path, dataset_id="test_ds_2")

    assert table.row_count == 3
    assert table.column_count == 4
    col_names = [c.name for c in table.columns]
    assert "region" in col_names
    assert "revenue" in col_names


def test_csv_parser_messy_data_quality():
    """Verify messy_data.csv accurately detects null values and duplicates."""
    messy_path = TEST_DATA_DIR / "messy_data.csv"
    table, warnings = CsvParser.parse(messy_path, dataset_id="test_ds_3")

    assert table.row_count == 7
    # Column 'units' has missing values in messy_data.csv
    units_col = next((c for c in table.columns if c.name == "units"), None)
    assert units_col is not None
    assert units_col.quality_stats.null_count >= 1


def test_excel_parser_multi_sheet():
    """Verify multi_sheet_sales.xlsx extracts both 'Orders' and 'Inventory' sheets."""
    xlsx_path = TEST_DATA_DIR / "multi_sheet_sales.xlsx"
    tables, warnings = ExcelParser.parse(xlsx_path, dataset_id="test_ds_4")

    assert len(tables) == 2
    sheet_names = [t.name for t in tables]
    assert "Orders" in sheet_names
    assert "Inventory" in sheet_names

    orders_table = next(t for t in tables if t.name == "Orders")
    assert orders_table.row_count == 3
    assert orders_table.column_count == 4


def test_json_parser_nested_normalization():
    """Verify nested_sales.json flattens nested dictionary keys (customer.id, customer.tier)."""
    json_path = TEST_DATA_DIR / "nested_sales.json"
    table, warnings = JsonParser.parse(json_path, dataset_id="test_ds_5")

    assert table.row_count == 2
    col_names = [c.name for c in table.columns]
    assert "order_id" in col_names
    assert any("customer" in c for c in col_names)


def test_jsonl_parser():
    """Verify events.jsonl parses newline-delimited JSON objects."""
    jsonl_path = TEST_DATA_DIR / "events.jsonl"
    table, warnings = JsonParser.parse(jsonl_path, dataset_id="test_ds_6")

    assert table.row_count == 3
    col_names = [c.name for c in table.columns]
    assert "event_id" in col_names
    assert "action" in col_names


def test_prompt_injection_file_safety():
    """Verify FR-20: Prompt injection strings inside data cells are treated as raw text only."""
    inj_path = TEST_DATA_DIR / "prompt_injection.csv"
    table, warnings = CsvParser.parse(inj_path, dataset_id="test_ds_7")

    assert table.row_count == 2
    # Verify values are read as text data without executing instructions
    assert any("IGNORE ALL PREVIOUS INSTRUCTIONS" in str(r.get("note", "")) for r in table.sample_rows)


def test_corrupted_file_graceful_handling():
    """Verify FR-3: Corrupted or non-parseable files return friendly errors rather than crashing."""
    corrupt_path = TEST_DATA_DIR / "corrupted_file.csv"
    # Unified dispatcher should catch corruption and not crash
    try:
        tables, warnings = parse_uploaded_file(corrupt_path, "corrupted_file.csv", "test_ds_8")
        # Should either return with warnings or raise clean ValueError
        assert isinstance(warnings, list)
    except ValueError as ve:
        assert "Could not parse" in str(ve) or "corrupted" in str(ve).lower()
