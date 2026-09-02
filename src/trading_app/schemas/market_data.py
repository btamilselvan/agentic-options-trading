"""Raw market-data contracts: Candle, Quote, OptionContract
(requirements.md section 5)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from trading_app.schemas.common import VersionedModel


class DataFreshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"


class Interval(StrEnum):
    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    DAILY = "1d"


class Candle(VersionedModel):
    symbol: str
    interval: Interval
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    market_timestamp: datetime
    source: str
    freshness: DataFreshness = DataFreshness.FRESH


class Quote(VersionedModel):
    symbol: str
    option_contract_id: str | None = None
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    market_timestamp: datetime
    source: str
    freshness: DataFreshness = DataFreshness.FRESH


class OptionRight(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


class OptionContract(VersionedModel):
    underlying: str
    expiration: datetime
    strike: float
    right: OptionRight
    contract_id: str
    quote: Quote | None = None
    iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    greeks_available: bool = False
    source: str
