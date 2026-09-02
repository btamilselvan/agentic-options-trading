"""LLM-insight contracts: SetupEvaluationRequest, SetupEvaluationResponse
(requirements.md section 4.4).

The request is a compact, bounded context package — never raw unbounded
candle streams, never credentials or account identifiers, and never a tool
that can execute an order. The response must validate against a strict JSON
schema; on failure the evaluation is unavailable, never a fallback
executable path.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from trading_app.schemas.common import VersionedModel
from trading_app.schemas.features import FeatureEvent, FeatureSnapshot


class SetupType(StrEnum):
    VWAP_RECLAIM = "vwap_reclaim"
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    TREND_CONTINUATION = "trend_continuation"
    NONE = "none"


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SetupEvaluationRequest(VersionedModel):
    symbol: str
    triggering_event: FeatureEvent
    current_snapshot: FeatureSnapshot
    recent_history: list[FeatureSnapshot] = Field(default_factory=list)
    market_context: dict[str, float | str | None] = Field(default_factory=dict)
    candidate_option_contracts: list[str] = Field(default_factory=list)
    permitted_setup_types: list[SetupType]
    advisory_only_notice: str = (
        "Output is advisory only and cannot issue, modify, or cancel an order."
    )


class SetupEvaluationResponse(VersionedModel):
    request_id: str
    setup_available: bool
    setup_type: SetupType
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    time_horizon_minutes: int = Field(ge=0)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
    data_quality_concerns: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    provider: str
    model_name: str
    prompt_version: str
