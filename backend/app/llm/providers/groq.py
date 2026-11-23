# backend/app/llm/providers/groq.py
# Groq LLM provider implementation with two-stage safe planning, pandas execution, and grounding.

import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
import pandas as pd

from backend.app.llm.base import BaseLLMProvider, LLMResult
from backend.app.llm.safe_plans import SafePlan, SafePlanExecutor, OperationResult
from backend.app.llm.context_builder import ContextBuilder
from backend.app.llm.fallback import DeterministicFallbackProvider
from backend.app.insights.validator import InsightValidator

logger = logging.getLogger("insightforge.chat.groq")

PREFERRED_FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]


class GroqProvider(BaseLLMProvider):
    """Integrates Groq chat completions API with two-stage plan validation and pandas grounding."""

    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b") -> None:
        self.api_key = api_key
        self.model = model or "openai/gpt-oss-120b"
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    async def _call_api(self, model_name: str, messages: List[Dict[str, str]], json_mode: bool = False) -> Optional[str]:
        """Executes HTTP request to Groq API with optional JSON mode."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(self.url, headers=headers, json=body)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            logger.warning(f"Groq API model {model_name} returned HTTP {res.status_code}: {res.text}")
            return None

    def _sanitize_history(self, chat_history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Maps 'analyst' role to standard 'assistant' role for OpenAI/Groq compatibility."""
        sanitized: List[Dict[str, str]] = []
        if not chat_history:
            return sanitized

        for msg in chat_history[-4:]:
            role = msg.get("role", "user")
            if role == "analyst":
                role = "assistant"
            elif role not in ["user", "assistant", "system"]:
                role = "user"
            sanitized.append({"role": role, "content": msg.get("content", msg.get("text", ""))})
        return sanitized

    async def _plan_with_model(
        self,
        question: str,
        df: pd.DataFrame,
        dataset: Optional[Any],
        chat_history: Optional[List[Dict[str, str]]],
    ) -> Optional[SafePlan]:
        """Asks Groq to choose a SafePlan JSON from dataset context. Retries once on validation error."""
        context = ContextBuilder.build_planning_context(df, dataset)
        prompt_text = ContextBuilder.format_planning_prompt(context, question)

        messages = [
            {"role": "system", "content": "You are a deterministic planning agent. You select only allowed analytical operations and return valid JSON."},
        ]
        messages.extend(self._sanitize_history(chat_history))
        messages.append({"role": "user", "content": prompt_text})

        candidate_models = [self.model] + [m for m in PREFERRED_FALLBACK_MODELS if m != self.model]

        for model_to_try in candidate_models:
            try:
                raw_json = await self._call_api(model_to_try, messages, json_mode=True)
                if not raw_json:
                    continue

                # Strip markdown code blocks if present
                clean_json = re.sub(r"^```json\s*", "", raw_json.strip())
                clean_json = re.sub(r"\s*```$", "", clean_json)

                try:
                    plan_data = json.loads(clean_json)
                    plan = SafePlan(**plan_data)
                    logger.info(f"Groq successfully planned: operation={plan.operation}")
                    return plan
                except Exception as val_err:
                    logger.warning(f"Validation error on plan from {model_to_try}: {val_err}. Retrying once...")
                    # Retry once with validation error included
                    retry_messages = messages + [
                        {"role": "assistant", "content": clean_json},
                        {"role": "user", "content": f"The JSON failed validation: {val_err}. Please fix the JSON and return valid SafePlan JSON."},
                    ]
                    retry_raw = await self._call_api(model_to_try, retry_messages, json_mode=True)
                    if retry_raw:
                        retry_clean = re.sub(r"^```json\s*", "", retry_raw.strip())
                        retry_clean = re.sub(r"\s*```$", "", retry_clean)
                        plan = SafePlan(**json.loads(retry_clean))
                        return plan
            except Exception as e:
                logger.warning(f"Error during Groq planning with {model_to_try}: {e}")

        return None

    async def ask_grounded(
        self,
        question: str,
        analysis_metrics: Dict[str, Any],
        dataset_ids: List[str],
        domain: str = "general",
        chat_history: Optional[List[Dict[str, str]]] = None,
        dataset: Optional[Any] = None,
        df: Optional[pd.DataFrame] = None,
        analysis: Optional[Any] = None,
    ) -> LLMResult:
        # Load DataFrame if not supplied
        if df is None and dataset:
            from backend.app.analytics import load_dataset_dataframe
            df = load_dataset_dataframe(dataset)

        if df is None or df.empty:
            fallback = DeterministicFallbackProvider()
            return await fallback.ask_grounded(
                question=question,
                analysis_metrics=analysis_metrics,
                dataset_ids=dataset_ids,
                domain=domain,
                chat_history=chat_history,
                dataset=dataset,
                df=df,
                analysis=analysis,
            )

        # STAGE 1: PLAN SELECTION
        plan: Optional[SafePlan] = None
        try:
            plan = await self._plan_with_model(question, df, dataset, chat_history)
        except Exception as e:
            logger.warning(f"Plan selection exception: {e}")

        if not plan:
            logger.info("Using deterministic heuristic plan fallback")
            plan = SafePlanExecutor.determine_plan_heuristic(question, df, dataset=dataset, analysis=analysis)

        # STAGE 2: DETERMINISTIC EXECUTION (Python / Pandas)
        res: OperationResult = SafePlanExecutor.execute_safe_plan(plan, df, analysis=analysis, dataset=dataset)
        sources = [f"{s.get('filename', 'dataset')}:{s.get('sheet', 'default')} (rows {s.get('rows', '1-all')})" for s in res.source_references]
        limitations = res.limitations + [f"Grounded AI: operations executed by Python pandas; explained via Groq ({self.model})."]

        # If data is missing or unanswerable, return honest response immediately
        if res.status == "missing_data" or plan.operation == "unanswerable":
            fallback = DeterministicFallbackProvider()
            return await fallback.ask_grounded(
                question=question,
                analysis_metrics=analysis_metrics,
                dataset_ids=dataset_ids,
                domain=domain,
                chat_history=chat_history,
                dataset=dataset,
                df=df,
                analysis=analysis,
            )

        # If clarification is needed
        if res.status == "clarification_needed":
            return LLMResult(
                text=f"I could not understand which field you mean: {res.clarification_question}",
                computed_evidence=res.values,
                sources=sources,
                limitations=limitations,
                used_fallback=False,
                safe_plan_executed=plan.operation,
            )

        # STAGE 3: EXPLANATION SYNTHESIS WITH STRICT GROUNDING
        system_msg = (
            "You are the Infosys AI Grounded Business Analyst.\n"
            "RULE 1: Never invent numbers. All calculations have already been performed by Python pandas.\n"
            "RULE 2: Cite numbers EXACTLY as provided in COMPUTED EVIDENCE. Do not round, alter, or synthesize numbers.\n"
            "RULE 3: Use bullet points (•) rather than numbered lists.\n"
            "RULE 4: Be concise, professional, and directly answer the question.\n"
            "RULE 5: If the evidence does not contain a specific detail, state that it is not available in the dataset."
        )

        user_content = (
            f"User Question: \"{question}\"\n\n"
            f"<COMPUTED_EVIDENCE>\n{json.dumps(res.values, indent=2)}\n</COMPUTED_EVIDENCE>\n"
            f"Domain: {domain}"
        )

        messages = [{"role": "system", "content": system_msg}]
        messages.extend(self._sanitize_history(chat_history))
        messages.append({"role": "user", "content": user_content})

        candidate_models = [self.model] + [m for m in PREFERRED_FALLBACK_MODELS if m != self.model]

        for model_to_try in candidate_models:
            try:
                raw_text = await self._call_api(model_to_try, messages)
                if raw_text:
                    is_valid, unverified = InsightValidator.validate_insight(
                        observed_fact=raw_text,
                        evidence=res.values,
                        all_metrics=analysis_metrics,
                    )

                    if is_valid:
                        return LLMResult(
                            text=raw_text,
                            computed_evidence=res.values,
                            sources=sources,
                            limitations=limitations,
                            used_fallback=False,
                            safe_plan_executed=plan.operation,
                            table_payload=res.table_payload,
                            chart_payload=res.chart_payload,
                        )
                    else:
                        logger.warning(f"Groq FR-16 Guard blocked numbers: {unverified}. Falling back to templated math.")
            except Exception as e:
                logger.warning(f"Groq error explaining with {model_to_try}: {e}")

        # Fallback to templated explanation if LLM generation was shielded or unavailable
        fallback = DeterministicFallbackProvider()
        fallback_res = await fallback.ask_grounded(
            question=question,
            analysis_metrics=analysis_metrics,
            dataset_ids=dataset_ids,
            domain=domain,
            chat_history=chat_history,
            dataset=dataset,
            df=df,
            analysis=analysis,
        )
        fallback_res.limitations.append("AI explanation bypassed or shielded; deterministic fallback executed.")
        return fallback_res
