# backend/tests/demo_analytics.py
# Verification script for live Phase 3 analytics pipeline.

import requests
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "test_data" / "clean_sales.csv"

with open(DATA_FILE, "rb") as f:
    up = requests.post("http://127.0.0.1:8000/api/upload", files=[("files", ("clean_sales.csv", f, "text/csv"))])
    ds_id = up.json()["datasets"][0]["id"]

an = requests.post(f"http://127.0.0.1:8000/api/datasets/{ds_id}/analyze").json()
m = an["metrics"]

print("=== Live Analytics Verification (Phase 3) ===")
print("Analysis ID:", an["id"])
print("Domain Inferred:", an["domain"])
print(f"Total Revenue: ${m['total_revenue']:,.2f}")
print(f"Total Cost:    ${m['total_cost']:,.2f}")
print(f"Gross Profit:  ${m['gross_profit']:,.2f}")
print(f"Gross Margin:  {m['gross_margin_percentage']}%")
print(f"Average Order: ${m['average_order_value']:,.2f}")
print(f"Top Category:  {m['category_breakdown'][0]['category']} (${m['category_breakdown'][0]['value']:,.2f}, {m['category_breakdown'][0]['percentage_of_total']}%)")
print(f"Top Product:   {m['top_products'][0]['name']} (${m['top_products'][0]['value']:,.2f})")
print(f"Top Customer:  {m['top_customers'][0]['name']} (${m['top_customers'][0]['value']:,.2f})")
print(f"Monthly Growth Rate: {m['time_series_growth']['overall_growth_rate']}% ({m['time_series_growth']['trend_direction']})")
print("Verified Insight Cards Built:", len(an["insights"]))
for idx, ins in enumerate(an["insights"], 1):
    print(f"\n  [{ins['priority'].upper()}] Insight {idx}: {ins['title']}")
    print(f"    Fact:           {ins['observed_fact']}")
    print(f"    Interpretation: {ins['interpretation']}")
    print(f"    Action:         {ins['recommendation']}")
    print(f"    Formula:        {ins['method_or_formula']}")
