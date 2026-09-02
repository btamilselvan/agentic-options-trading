"""InsightProvider interface (requirements.md section 4.4).

Application code must depend on this interface, never on a concrete
provider/model name — provider selection is configuration only
(`LLM__PROVIDER`), so switching from Gemini to a local Ollama model (or
back) never requires a code change. See `factory.get_insight_provider`.
"""
from __future__ import annotations

from typing import Protocol

from trading_app.schemas.insights import SetupEvaluationRequest, SetupEvaluationResponse


class InsightProviderError(Exception):
    """Raised when a provider call fails, times out, or returns output that
    does not validate against `SetupEvaluationResponse`. Callers must treat
    this as "evaluation unavailable" and must never fabricate an
    executable result (requirements.md sections 4.4, 12)."""


class InsightProvider(Protocol):
    async def evaluate_setup(
        self, request: SetupEvaluationRequest
    ) -> SetupEvaluationResponse: ...


# The fields an LLM is actually asked to produce. Administrative fields on
# SetupEvaluationResponse (schema_version, correlation_id, created_at,
# provider, model_name, prompt_version) are populated by our own code, not
# the model, so they are deliberately excluded here — mirrors the example
# contract in requirements.md section 4.4.
LLM_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string"},
        "setup_available": {"type": "boolean"},
        "setup_type": {
            "type": "string",
            "enum": ["vwap_reclaim", "opening_range_breakout", "trend_continuation", "none"],
        },
        "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "confidence": {"type": "number"},
        "time_horizon_minutes": {"type": "integer"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "invalidation_conditions": {"type": "array", "items": {"type": "string"}},
        "data_quality_concerns": {"type": "array", "items": {"type": "string"}},
        "requires_human_review": {"type": "boolean"},
    },
    "required": [
        "request_id",
        "setup_available",
        "setup_type",
        "direction",
        "confidence",
        "time_horizon_minutes",
        "requires_human_review",
    ],
}


def merge_response_fields(
    data: dict,
    *,
    request: SetupEvaluationRequest,
    provider: str,
    model_name: str,
    prompt_version: str,
) -> dict:
    """Combine the model's raw JSON with the fields our own code owns.
    Shared by every provider so the merge policy can't drift between them."""
    return {
        **data,
        "request_id": data.get("request_id") or str(request.correlation_id),
        "provider": provider,
        "model_name": model_name,
        "prompt_version": prompt_version,
    }
