# backend/app/routes/analysis.py
# Endpoints to trigger analytics jobs and retrieve verifiable metrics & insight evidence (FR-12, FR-13, FR-16).

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from backend.app.models.insight import AnalysisModel
from backend.app.storage.sqlite_store import store
from backend.app.analytics import run_analytics_pipeline
from backend.app.insights.builder import InsightBuilder

router = APIRouter(tags=["Analysis"])


@router.post("/datasets/{dataset_id}/analyze", response_model=AnalysisModel)
def run_dataset_analysis(dataset_id: str) -> AnalysisModel:
    """
    Executes deterministic analytics pipeline on the given dataset.
    Computes summary stats, category breakdowns, growth metrics, and builds verified insight cards.
    """
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    # 1. Run deterministic Pandas computations
    results = run_analytics_pipeline(dataset)
    metrics = results["metrics"]
    charts = results["charts"]
    domain = results["domain"]
    analysis_id = f"analysis_{dataset_id[:8]}"

    # 2. Synthesize verified, rule-ranked, FR-16 validated insight objects
    insights = InsightBuilder.build_insights(
        analysis_id=analysis_id,
        dataset=dataset,
        metrics=metrics,
    )

    analysis = AnalysisModel(
        id=analysis_id,
        dataset_ids=[dataset_id],
        domain=domain,
        configuration={"supported_features": results["supported_features"]},
        metrics=metrics,
        charts=charts,
        insights=insights,
    )
    store.save_analysis(analysis)
    return analysis


@router.get("/analyses/{analysis_id}", response_model=AnalysisModel)
def get_analysis(analysis_id: str) -> AnalysisModel:
    """Retrieve computed metrics, chart series, and prioritized insights."""
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return analysis


@router.get("/analyses/{analysis_id}/insights/{insight_id}/evidence")
def get_insight_evidence(analysis_id: str, insight_id: str) -> Dict[str, Any]:
    """
    Audit endpoint: Returns exact source rows, formula, and numbers behind an insight card.
    Guarantees that no number was hallucinated by an LLM.
    """
    evidence = store.get_insight_evidence(analysis_id, insight_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence for insight '{insight_id}' in analysis '{analysis_id}' not found.",
        )
    return evidence
