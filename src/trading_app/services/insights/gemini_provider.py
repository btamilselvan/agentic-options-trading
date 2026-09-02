"""Gemini-backed InsightProvider.

Calls the plain Gemini `generateContent` REST endpoint directly rather than
pulling in a provider-specific SDK, so adding a provider never grows the
dependency surface. Model name, timeout, and retry policy are configuration
(requirements.md section 4.4) — verify the configured model name against
the currently available Gemini API models before relying on it.
"""
from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from trading_app.config import LLMSettings
from trading_app.schemas.insights import SetupEvaluationRequest, SetupEvaluationResponse
from trading_app.security.secrets import SecretsProvider
from trading_app.services.insights.base import (
    LLM_OUTPUT_SCHEMA,
    InsightProviderError,
    merge_response_fields,
)

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_PROMPT_VERSION = "1.0"


class GeminiInsightProvider:
    def __init__(self, settings: LLMSettings, secrets: SecretsProvider) -> None:
        self._settings = settings
        self._secrets = secrets

    async def evaluate_setup(self, request: SetupEvaluationRequest) -> SetupEvaluationResponse:
        api_key = self._secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise InsightProviderError("GEMINI_API_KEY is not configured.")

        url = f"{_API_BASE}/models/{self._settings.model_name}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": request.model_dump_json()}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": LLM_OUTPUT_SCHEMA,
            },
        }

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for attempt in range(self._settings.max_retries + 1):
                try:
                    response = await client.post(url, params={"key": api_key}, json=payload)
                    response.raise_for_status()
                    body = response.json()
                    text = body["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text)
                    merged = merge_response_fields(
                        data,
                        request=request,
                        provider="gemini",
                        model_name=self._settings.model_name,
                        prompt_version=_PROMPT_VERSION,
                    )
                    return SetupEvaluationResponse.model_validate(merged)
                except (
                    httpx.HTTPError,
                    KeyError,
                    IndexError,
                    json.JSONDecodeError,
                    ValidationError,
                ) as exc:
                    last_error = exc
                    logger.warning("Gemini insight call failed (attempt %d): %s", attempt, exc)

        raise InsightProviderError(f"Gemini evaluation failed: {last_error}") from last_error
