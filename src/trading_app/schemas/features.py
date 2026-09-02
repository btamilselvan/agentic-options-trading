"""Quantitative-engine and state-detection contracts: FeatureSnapshot,
FeatureEvent (requirements.md sections 4.2, 4.3, 5)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from trading_app.schemas.common import VersionedModel
from trading_app.schemas.market_data import DataFreshness


class FeatureSnapshot(VersionedModel):
    symbol: str
    as_of: datetime
    feature_definition_version: str
    features: dict[str, float | None] = Field(default_factory=dict)
    market_context: dict[str, float | str | None] = Field(default_factory=dict)
    data_quality: DataFreshness = DataFreshness.FRESH


class FeatureEventDomain(StrEnum):
    VWAP = "VWAP"
    EMA_STRUCTURE = "EMA_STRUCTURE"
    KEY_LEVEL = "KEY_LEVEL"
    VOLUME = "VOLUME"
    MARKET_REGIME = "MARKET_REGIME"
    DATA_QUALITY = "DATA_QUALITY"


class FeatureEvent(VersionedModel):
    symbol: str
    domain: FeatureEventDomain
    event_type: str
    old_state: str | None = None
    new_state: str
    evidence: dict[str, float | str | None] = Field(default_factory=dict)
    event_timestamp: datetime
    feature_definition_version: str
    severity: str = "info"
