# backend/app/routes/reports.py
# Endpoints for generating, inspecting, and downloading multi-section PDF reports and CSV exports (FR-22, FR-23, FR-24).

import io
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from backend.app.storage.sqlite_store import store
from backend.app.reports.report_builder import ReportBuilder, StructuredReport
from backend.app.reports.pdf_export import generate_executive_pdf

router = APIRouter(tags=["Reports & Exports"])


@router.get("/reports/{analysis_id}/sections", response_model=StructuredReport)
def get_report_sections(analysis_id: str) -> StructuredReport:
    """
    Returns the complete structured multi-section report (FR-22).
    Allows interactive preview in the browser before download.
    """
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return ReportBuilder.build_report(analysis)


@router.get("/reports/{analysis_id}/csv")
def download_analysis_csv(analysis_id: str) -> Response:
    """Download metrics and insights formatted as a clean, auditable CSV file (FR-24)."""
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )

    output = io.StringIO()
    output.write("section,metric_or_key,value,formula_or_notes\n")
    # 1. Summary Metrics
    for k, v in analysis.metrics.items():
        if isinstance(v, (int, float, str, bool)):
            output.write(f'"Summary Metric","{k}","{v}","Deterministic calculation"\n')

    # 2. Insights
    for ins in analysis.insights:
        output.write(
            f'"Insight","[{ins.priority.upper()}] {ins.title}","{ins.observed_fact}","Formula: {ins.method_or_formula} | Action: {ins.recommendation}"\n'
        )

    # 3. Category Breakdown
    if "category_breakdown" in analysis.metrics:
        for cat in analysis.metrics["category_breakdown"]:
            output.write(
                f'"Category Share","{cat.get("category")}","${cat.get("value", 0):,.2f}","{cat.get("percentage_of_total", 0)}%"\n'
            )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=insightforge_report_{analysis_id}.csv"},
    )


@router.get("/reports/{analysis_id}/pdf")
def download_analysis_pdf(analysis_id: str) -> StreamingResponse:
    """Download verified, multi-page executive PDF report built via ReportLab (FR-22, FR-24)."""
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )

    pdf_buffer = generate_executive_pdf(analysis)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=insightforge_report_{analysis_id}.pdf"},
    )
