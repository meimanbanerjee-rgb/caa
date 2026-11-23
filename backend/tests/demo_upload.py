# backend/tests/demo_upload.py
# Verification script demonstrating live upload, parsing, and schema extraction.

import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "test_data"

with open(BASE_DIR / "clean_sales.csv", "rb") as f1, open(BASE_DIR / "multi_sheet_sales.xlsx", "rb") as f2:
    files = [
        ("files", ("clean_sales.csv", f1, "text/csv")),
        ("files", ("multi_sheet_sales.xlsx", f2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
    ]
    resp = requests.post("http://127.0.0.1:8000/api/upload", files=files)
    print("HTTP Status Code:", resp.status_code)
    data = resp.json()
    print("Uploaded Files Count:", data["count"])
    for ds in data["datasets"]:
        print(f"Dataset ID: {ds['id']}")
        print(f"Filename: {ds['filename']} (Format: {ds['file_type']}, Status: {ds['status']})")
        print(f"Tables Found: {len(ds['tables'])}")
        for t in ds["tables"]:
            print(f"  - Sheet/Table: '{t['name']}' ({t['row_count']} rows, {t['column_count']} cols)")
            print(f"    Columns: {[c['name'] for c in t['columns'][:6]]}...")
            print(f"    Sample Row: {t['sample_rows'][0] if t['sample_rows'] else 'None'}")
        print("-" * 50)
