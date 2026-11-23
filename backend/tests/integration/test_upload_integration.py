# backend/tests/integration/test_upload_integration.py
# End-to-end integration tests verifying upload, parsing, deterministic analysis, and evidence auditing.

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def test_upload_clean_sales_csv():
    """Verify upload of clean_sales.csv creates a profiled dataset with parsed tables."""
    csv_file = TEST_DATA_DIR / "clean_sales.csv"
    with open(csv_file, "rb") as f:
        response = client.post(
            "/api/upload",
            files=[("files", ("clean_sales.csv", f, "text/csv"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    ds = data["datasets"][0]
    assert ds["filename"] == "clean_sales.csv"
    assert ds["file_type"] == "csv"
    assert ds["status"] == "profiled"
    assert len(ds["tables"]) == 1

    table = ds["tables"][0]
    assert table["row_count"] == 10
    assert table["column_count"] == 11
    assert len(table["columns"]) == 11
    assert len(table["sample_rows"]) == 10


def test_upload_multi_sheet_excel():
    """Verify upload of multi_sheet_sales.xlsx creates a dataset with multiple independent tables."""
    excel_file = TEST_DATA_DIR / "multi_sheet_sales.xlsx"
    with open(excel_file, "rb") as f:
        response = client.post(
            "/api/upload",
            files=[("files", ("multi_sheet_sales.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )

    assert response.status_code == 200
    data = response.json()
    ds = data["datasets"][0]
    assert ds["file_type"] == "xlsx"
    assert len(ds["tables"]) == 2
    sheet_names = [t["name"] for t in ds["tables"]]
    assert "Orders" in sheet_names
    assert "Inventory" in sheet_names


def test_upload_corrupted_json_returns_warning_not_crash():
    """Verify FR-3: Corrupted or unparseable files yield clear warnings and do not crash the service."""
    corrupt_file = TEST_DATA_DIR / "corrupted_json.json"
    with open(corrupt_file, "rb") as f:
        response = client.post(
            "/api/upload",
            files=[("files", ("corrupted_json.json", f, "application/json"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert "warnings" in data
    assert data["count"] == 1
    ds = data["datasets"][0]
    assert ds["status"] == "error"
    assert any("Parsing error" in w for w in ds["warnings"])


def test_end_to_end_analysis_and_evidence_audit():
    """
    CRITICAL END-TO-END FLOW:
    Upload clean_sales.csv -> Trigger POST /api/datasets/{id}/analyze ->
    Verify hand-calculated metrics -> Audit insight evidence via GET /api/analyses/{id}/insights/{insight_id}/evidence.
    """
    csv_file = TEST_DATA_DIR / "clean_sales.csv"
    with open(csv_file, "rb") as f:
        up_resp = client.post(
            "/api/upload",
            files=[("files", ("clean_sales_e2e.csv", f, "text/csv"))],
        )

    assert up_resp.status_code == 200
    dataset_id = up_resp.json()["datasets"][0]["id"]

    # Trigger analysis pipeline
    an_resp = client.post(f"/api/datasets/{dataset_id}/analyze")
    assert an_resp.status_code == 200
    analysis = an_resp.json()

    # Verify deterministic calculations match ground truth
    metrics = analysis["metrics"]
    assert metrics["total_revenue"] == 28100.00
    assert metrics["gross_margin_percentage"] == 40.68
    assert metrics["average_order_value"] == 2810.00
    assert metrics["row_count"] == 10

    # Verify insight structure with triple separation (FR-16)
    assert len(analysis["insights"]) >= 2
    ins = analysis["insights"][0]
    assert "observed_fact" in ins
    assert "interpretation" in ins
    assert "recommendation" in ins
    assert "evidence" in ins
    assert ins["evidence"]["total_revenue"] == 28100.00

    # Verify Evidence Audit endpoint
    ev_resp = client.get(f"/api/analyses/{analysis['id']}/insights/{ins['id']}/evidence")
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert ev_data["insight_id"] == ins["id"]
    assert ev_data["evidence"]["total_revenue"] == 28100.00
    assert "=" in ev_data["method_or_formula"] and "revenue" in ev_data["method_or_formula"]
