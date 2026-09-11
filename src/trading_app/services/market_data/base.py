"""MarketDataProvider interface.

The screener's only path to raw market data — no call site should depend
on a concrete provider (requirements.md sections 1, 4.2). Provider
selection is `MARKET_DATA__PROVIDER` config alone; see
`trading_app.services.market_data.factory`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from trading_app.schemas.market_data import Candle, DataFreshness, Interval


class MarketSnapshot(BaseModel):
    """A cheap, screener-level view of a symbol's current market state —
    NOT the canonical, versioned FeatureSnapshot the quantitative engine
    (component 2) will compute later. Raw inputs only; no substitute-with-
    zero for missing numbers (requirements.md section 5)."""

    symbol: str
    last_price: float | None = None
    prior_close: float | None = None
    session_volume: float | None = None
    avg_volume_baseline: float | None = None
    bid: float | None = None
    ask: float | None = None
    options_available: bool = False
    market_timestamp: datetime
    source: str
    freshness: DataFreshness = DataFreshness.FRESH


class MarketDataProviderError(Exception):
    """Raised when a provider cannot supply data for a symbol/universe.
    Callers must fail closed — never substitute a fabricated snapshot."""


class MarketDataProvider(Protocol):
    async def get_market_snapshots(self, symbols: list[str]) -> list[MarketSnapshot]: ...

    async def get_candles(
        self,
        symbol: str,
        interval: Interval,
        *,
        lookback_days: int,
        include_extended_hours: bool = False,
    ) -> list[Candle]:
        """OHLCV bar history for the quantitative engine (requirements.md
        section 4.2) — distinct from `get_market_snapshots`'s single
        current-state view. `lookback_days` is trading days, not calendar
        days. Bars are returned oldest-first."""
        ...
