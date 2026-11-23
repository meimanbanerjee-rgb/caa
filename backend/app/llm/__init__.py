# backend/app/llm/__init__.py
# Factory returning provider-independent LLM instance or offline deterministic fallback.

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.fallback import DeterministicFallbackProvider


def get_llm_provider() -> BaseLLMProvider:
    """
    Returns the configured LLM provider (Gemini, OpenAI, Anthropic),
    or falls back to 100% deterministic offline provider if no key is configured.
    """
    if not settings.is_ai_configured:
        return DeterministicFallbackProvider()

    provider = settings.llm_provider.lower().strip()
    key = settings.llm_api_key
    model = settings.llm_model

    if provider == "groq":
        from backend.app.llm.providers.groq import GroqProvider
        return GroqProvider(api_key=key, model=model if model else "llama-3.3-70b-versatile")
    elif provider == "gemini":
        from backend.app.llm.providers.gemini import GeminiProvider
        return GeminiProvider(api_key=key, model=model if model else "gemini-1.5-flash")
    elif provider == "openai":
        from backend.app.llm.providers.openai import OpenAIProvider
        return OpenAIProvider(api_key=key, model=model if model else "gpt-4o-mini")
    elif provider == "anthropic":
        from backend.app.llm.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=key, model=model if model else "claude-3-5-sonnet-20241022")

    return DeterministicFallbackProvider()

