# backend/tests/unit/test_config.py
# Unit tests verifying settings loading and key isolation rules.

from backend.app.config import settings


def test_settings_initialization():
    """Verify settings properties and safety rules."""
    assert settings.app_name == "InsightForge AI"
    assert settings.max_upload_mb > 0
    assert isinstance(settings.allowed_origins, list)
    assert len(settings.allowed_origins) > 0


def test_ai_key_configuration_state():
    """Verify that is_ai_configured reflects whether LLM_API_KEY is populated."""
    # In test environment with empty .env, AI should not be claimed as configured
    if not settings.llm_api_key:
        assert settings.is_ai_configured is False
    else:
        assert settings.is_ai_configured is True
