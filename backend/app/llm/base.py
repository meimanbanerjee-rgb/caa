# backend/app/llm/base.py
# Abstract interface for provider-independent grounded AI Analyst language models (PRD Section 5.5, 7).

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMResult(BaseModel):
    """Normalized response from any LLM provider or offline fallback."""
    text: str
    computed_evidence: Dict[str, Any] = Field(default_factory=dict)
    sources: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    used_fallback: bool = False
    safe_plan_executed: str = "get_summary"
    table_payload: Optional[List[Dict[str, Any]]] = None
    chart_payload: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract interface that all LLM implementations (Gemini, OpenAI, Anthropic, Fallback) must follow."""

    @abstractmethod
    async def ask_grounded(
        self,
        question: str,
        analysis_metrics: Dict[str, Any],
        dataset_ids: List[str],
        domain: str = "general",
        chat_history: Optional[List[Dict[str, str]]] = None,
        dataset: Optional[Any] = None,
        df: Optional[Any] = None,
        analysis: Optional[Any] = None,
    ) -> LLMResult:
        """
        Processes a user question about deterministic analysis metrics.
        Guarantees that responses cite only verified numbers computed by Python/pandas.
        """
        pass

