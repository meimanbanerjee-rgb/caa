# backend/app/routes/chat.py
# Chat endpoint for grounded AI analyst questions with safe step-by-step logging (FR-17 to FR-21).

import logging
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status

from backend.app.models.chat import ChatMessage, ChatRequest, ChatResponse
from backend.app.storage.sqlite_store import store
from backend.app.llm import get_llm_provider
from backend.app.analytics import load_dataset_dataframe

logger = logging.getLogger("insightforge.chat")
router = APIRouter(tags=["AI Analyst Chat"])


@router.post("/chat", response_model=ChatResponse)
async def ask_analyst(payload: ChatRequest) -> ChatResponse:
    """
    Submits a user question about a specific analysis.
    Grounds response purely in deterministic results; falls back to templated math when no key is set.
    Includes safe step-by-step audit logging (never logs API keys).
    """
    analysis = store.get_analysis(payload.analysis_id)
    if not analysis:
        logger.error(f"[CHAT ERROR] Analysis '{payload.analysis_id}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{payload.analysis_id}' not found.",
        )

    # Retrieve dataset and load DataFrame
    dataset = None
    df = None
    if analysis.dataset_ids:
        dataset = store.get_dataset(analysis.dataset_ids[0])
        if dataset:
            df = load_dataset_dataframe(dataset)

    # Safe step-by-step log 1: User question and dataset identification
    logger.info(
        f"[CHAT STEP 1] Question: \"{payload.question}\" | "
        f"Analysis: {payload.analysis_id} | "
        f"Dataset: {dataset.filename if dataset else 'None'} (id: {dataset.id if dataset else 'None'})"
    )

    # 1. Store user query in history
    now = datetime.now(timezone.utc)
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        role="user",
        text=payload.question,
        timestamp=now,
    )
    store.save_chat_message(payload.analysis_id, user_msg)

    # 2. Retrieve conversation history for context
    past_messages = store.get_chat_history(payload.analysis_id)
    history_ctx = [{"role": m.role, "text": m.text} for m in past_messages[-6:]]

    # 3. Ask configured grounded LLM or offline fallback
    provider = get_llm_provider()
    provider_name = type(provider).__name__
    logger.info(f"[CHAT STEP 2] Active provider: {provider_name}")

    try:
        result = await provider.ask_grounded(
            question=payload.question,
            analysis_metrics=analysis.metrics,
            dataset_ids=analysis.dataset_ids,
            domain=analysis.domain,
            chat_history=history_ctx,
            dataset=dataset,
            df=df,
            analysis=analysis,
        )

        # Safe step-by-step log 3: Interpreted intent, operation & validation
        logger.info(
            f"[CHAT STEP 3] Chosen operation: '{result.safe_plan_executed}' | "
            f"Fallback mode: {result.used_fallback} | "
            f"Sources: {result.sources}"
        )

        # Safe step-by-step log 4: Computed result summary (no raw full file contents)
        evidence_keys = list(result.computed_evidence.keys()) if result.computed_evidence else []
        summary_preview = {k: result.computed_evidence[k] for k in evidence_keys[:4]} if evidence_keys else {}
        logger.info(f"[CHAT STEP 4] Computed result summary keys: {evidence_keys} | Preview: {summary_preview}")

    except Exception as exc:
        logger.exception(f"[CHAT EXCEPTION] Error executing grounded analyst for query '{payload.question}': {str(exc)}")
        # Safe deterministic recovery
        from backend.app.llm.fallback import DeterministicFallbackProvider
        fallback = DeterministicFallbackProvider()
        result = await fallback.ask_grounded(
            question=payload.question,
            analysis_metrics=analysis.metrics,
            dataset_ids=analysis.dataset_ids,
            domain=analysis.domain,
            chat_history=history_ctx,
            dataset=dataset,
            df=df,
            analysis=analysis,
        )
        result.limitations.append(f"AI provider unavailable or encountered an error; deterministic fallback executed.")

    analyst_msg = ChatMessage(
        id=str(uuid.uuid4()),
        role="analyst",
        text=result.text,
        timestamp=datetime.now(timezone.utc),
        computed_evidence=result.computed_evidence,
        sources=result.sources,
        limitations=result.limitations,
        used_fallback=result.used_fallback,
        table_payload=result.table_payload,
        chart_payload=result.chart_payload,
    )
    store.save_chat_message(payload.analysis_id, analyst_msg)

    return ChatResponse(
        message=analyst_msg,
        safe_plan_executed=result.safe_plan_executed,
    )


@router.get("/chat/{analysis_id}", response_model=List[ChatMessage])
def get_chat_history(analysis_id: str) -> List[ChatMessage]:
    """Retrieve full conversation history for an analysis session."""
    return store.get_chat_history(analysis_id)
