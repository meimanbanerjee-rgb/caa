# backend/tests/unit/test_reports.py
# Unit tests for Report Builder, PDF Generation, and CSV Export (Phase 7, FR-22, FR-23, FR-24).

import pytest
from backend.app.models.insight import AnalysisModel, InsightModel, SourceReference, ReliabilityNote
from backend.app.reports.report_builder import ReportBuilder
from backend.app.reports.pdf_export import generate_executive_pdf


@pytest.fixture
def mock_analysis():
    return AnalysisModel(
        id="analysis_unit_test",
        dataset_ids=["ds_mock_1"],
        domain="ecommerce",
        configuration={"supported_features": ["financial_metrics", "category_breakdown"]},
        metrics={
            "row_count": 100,
            "column_count": 8,
            "total_revenue": 50000.0,
            "gross_profit": 20000.0,
            "gross_margin_percentage": 40.0,
            "average_order_value": 500.0,
            "category_breakdown": [
                {"category": "Electronics", "value": 35000.0, "percentage_of_total": 70.0},
                {"category": "Accessories", "value": 15000.0, "percentage_of_total": 30.0},
            ],
            "revenue_outliers": [
                {"row_index": 5, "identifier": "Enterprise Server", "value": 18000.0, "z_score": 3.1}
            ],
        },
        charts=[],
        insights=[
            InsightModel(
                id="ins_1",
                analysis_id="analysis_unit_test",
                title="Strong Margins in Electronics",
                category="revenue",
                plain_english_explanation="Healthy 40% margin observed.",
                priority="high",
                observed_fact="Gross margin is 40.0% across 100 transactions.",
                interpretation="Cost controls are effective.",
                recommendation="Reinvest gross profit in top inventory.",
                evidence={"margin": 40.0},
                method_or_formula="margin = profit / revenue",
                source=SourceReference(filename="sales.csv", sheet="Main", row_range="1-100"),
                reliability=ReliabilityNote(
                    statistical_confidence="High (N=100 rows)",
                    extraction_reliability="Direct parse (100%)",
                    judgment_uncertainty="Historical records",
                ),
                assumptions_and_limitations=[],
            )
        ],
    )


def test_report_builder_generates_all_required_sections(mock_analysis):
    """Verify FR-22: Report builder includes all standard executive sections."""
    report = ReportBuilder.build_report(mock_analysis)
    assert report.analysis_id == "analysis_unit_test"
    assert report.domain == "ecommerce"

    section_ids = [s.id for s in report.sections]
    assert "executive_summary" in section_ids
    assert "dataset_overview" in section_ids
    assert "key_metrics" in section_ids
    assert "prioritized_findings" in section_ids
    assert "category_breakdown" in section_ids
    assert "risks" in section_ids
    assert "opportunities" in section_ids
    assert "methodology_and_audit" in section_ids


def test_report_builder_omits_irrelevant_sections():
    """Verify FR-22: Omit revenue/risk sections if data lacks relevant metrics."""
    minimal_analysis = AnalysisModel(
        id="analysis_minimal",
        dataset_ids=["ds_min"],
        domain="general",
        configuration={},
        metrics={"row_count": 20, "column_count": 3},
        charts=[],
        insights=[],
    )
    report = ReportBuilder.build_report(minimal_analysis)
    section_ids = [s.id for s in report.sections]
    # Key metrics, category breakdown, and risks should be omitted if no data supports them
    assert "category_breakdown" not in section_ids
    assert "risks" not in section_ids


def test_pdf_export_generates_valid_pdf_stream(mock_analysis):
    """Verify FR-24: ReportLab generates a valid PDF buffer starting with %PDF."""
    pdf_buffer = generate_executive_pdf(mock_analysis)
    pdf_bytes = pdf_buffer.getvalue()

    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
