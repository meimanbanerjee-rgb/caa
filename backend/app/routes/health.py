# backend/app/routes/health.py
# System health and AI provider configuration status endpoint.

from typing import Any, Dict
from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health() -> Dict[str, Any]:
    """
    Returns server operational status and indicates if an external AI key is active.
    When ai_configured is false, InsightForge operates in full deterministic mode.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "ai_configured": settings.is_ai_configured,
        "provider": settings.llm_provider,
        "model": settings.llm_model if settings.is_ai_configured else "offline-deterministic",
        "max_upload_mb": settings.max_upload_mb,
    }
