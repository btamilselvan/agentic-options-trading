"""Ollama-backed InsightProvider for local models.

No API key required — point `LLM__OLLAMA_BASE_URL` at a running local
Ollama daemon (`ollama serve`, default `http://localhost:11434`), set
`LLM__PROVIDER=ollama`, and `LLM__MODEL_NAME` to a model you've pulled
locally (`ollama pull <model>`).
"""
from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from trading_app.config import LLMSettings
from trading_app.schemas.insights import SetupEvaluationRequest, SetupEvaluationResponse
from trading_app.services.insights.base import (
    LLM_OUTPUT_SCHEMA,
    InsightProviderError,
    merge_response_fields,
)

logger = logging.getLogger(__name__)

_PROMPT_VERSION = "1.0"


class OllamaInsightProvider:
    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    async def evaluate_setup(self, request: SetupEvaluationRequest) -> SetupEvaluationResponse:
        url = f"{self._settings.ollama_base_url}/api/chat"
        payload = {
            "model": self._settings.model_name,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only JSON matching this schema, no other text: "
                        f"{json.dumps(LLM_OUTPUT_SCHEMA)}"
                    ),
                },
                {"role": "user", "content": request.model_dump_json()},
            ],
        }

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for attempt in range(self._settings.max_retries + 1):
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    body = response.json()
                    data = json.loads(body["message"]["content"])
                    merged = merge_response_fields(
                        data,
                        request=request,
                        provider="ollama",
                        model_name=self._settings.model_name,
                        prompt_version=_PROMPT_VERSION,
                    )
                    return SetupEvaluationResponse.model_validate(merged)
                except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
                    last_error = exc
                    logger.warning("Ollama insight call failed (attempt %d): %s", attempt, exc)

        raise InsightProviderError(f"Ollama evaluation failed: {last_error}") from last_error
