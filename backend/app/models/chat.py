# backend/app/models/chat.py
# Pydantic schemas for the AI Analyst chat interface.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """An individual message exchanged in an AI Analyst consultation."""
    id: Optional[str] = None
    role: str  # 'user', 'analyst', 'system'
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    computed_evidence: Dict[str, Any] = Field(default_factory=dict)
    sources: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    used_fallback: bool = False
    table_payload: Optional[List[Dict[str, Any]]] = None
    chart_payload: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Payload sent by the frontend to interrogate an analysis."""
    analysis_id: str
    question: str
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response returned by the grounded AI analyst."""
    message: ChatMessage
    safe_plan_executed: Optional[str] = None
