# backend/app/main.py
# Primary FastAPI application entry point, registering routes and configuring CORS.

# pyrefly: ignore[missing-import]
from fastapi import FastAPI
# pyrefly: ignore[missing-import]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.routes import (
    health,
    upload,
    datasets,
    analysis,
    chat,
    reports,
    history,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Deterministic Business Intelligence Engine with Grounded AI Explanations",
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes with /api prefix
app.include_router(health.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(history.router, prefix="/api")


@app.get("/")
def root():
    """Root redirect / greeting providing API discovery information."""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs_url": "/docs",
        "health_check": "/api/health",
        "ai_active": settings.is_ai_configured,
    }
