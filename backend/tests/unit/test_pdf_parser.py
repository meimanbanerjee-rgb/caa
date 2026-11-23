# backend/tests/unit/test_pdf_parser.py
# Unit tests for PDF narrative and table extraction with page references (Phase 6, FR-1 to FR-4).

from pathlib import Path
import pytest
from backend.app.ingestion.pdf_parser import PdfParser

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def test_pdf_parser_extracts_narrative_and_tables():
    """Verify PdfParser extracts structured table rows and narrative text with page references."""
    pdf_path = TEST_DATA_DIR / "sample_report.pdf"
    assert pdf_path.exists()

    tables, warnings = PdfParser.parse(pdf_path, dataset_id="ds_pdf_test")
    assert len(tables) >= 2

    # Check narrative table exists
    narrative_table = next((t for t in tables if "Narrative" in t.name), None)
    assert narrative_table is not None
    assert narrative_table.row_count > 0

    # Verify page references are preserved (FR-4)
    sample_text_rows = narrative_table.sample_rows
    assert any("Page 1" in str(r.get("source_reference", "")) for r in sample_text_rows)
    assert any("Quarterly Business Review" in str(r.get("text_content", "")) for r in sample_text_rows)

    # Check extracted data table
    data_table = next((t for t in tables if "Extracted Table" in t.name), None)
    assert data_table is not None
    assert data_table.row_count >= 3
    col_names = [c.name.lower() for c in data_table.columns]
    assert any("product" in c for c in col_names)
    assert any("revenue" in c for c in col_names)


def test_pdf_parser_corrupted_file_handling():
    """Verify FR-3: Corrupted PDF yields clear exception/message instead of crash."""
    corrupted_path = TEST_DATA_DIR / "corrupted_file.csv"  # Non-PDF binary fed to pdf parser
    with pytest.raises(ValueError, match="Could not open or parse PDF file"):
        PdfParser.parse(corrupted_path, dataset_id="ds_corrupted_pdf")

