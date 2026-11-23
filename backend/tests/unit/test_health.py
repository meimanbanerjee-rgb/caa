# backend/tests/unit/test_health.py
# Unit tests verifying the /api/health endpoint and service status.

# pyrefly: ignore[missing-import]
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that /api/health responds with 200 and expected schema."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "InsightForge AI"
    assert "ai_configured" in data
    assert isinstance(data["ai_configured"], bool)
    assert "provider" in data
    assert "max_upload_mb" in data


def test_root_endpoint():
    """Verify that root / responds with service discovery information."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "InsightForge AI"
    assert data["docs_url"] == "/docs"
