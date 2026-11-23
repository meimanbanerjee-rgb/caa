# backend/app/routes/history.py
# Endpoint for retrieving historical analyses and audit logs.

from typing import List
from fastapi import APIRouter
from backend.app.models.insight import AnalysisModel
from backend.app.storage.sqlite_store import store

router = APIRouter(tags=["History"])


@router.get("/history", response_model=List[AnalysisModel])
def list_analysis_history() -> List[AnalysisModel]:
    """Retrieve all saved analyses and execution records."""
    return store.list_analyses()
