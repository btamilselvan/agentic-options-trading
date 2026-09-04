"""Screener output contract: CandidateSymbol (requirements.md section 4.1).

"Publish a CandidateSymbol record with symbol, score, reasons, timestamp,
and source-data freshness" — `as_of` is that timestamp (the market data's
own timestamp, not necessarily the record's creation time).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from trading_app.schemas.common import VersionedModel
from trading_app.schemas.market_data import DataFreshness


class CandidateSymbol(VersionedModel):
    symbol: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    as_of: datetime
    source_freshness: DataFreshness = DataFreshness.FRESH
    run_id: str
