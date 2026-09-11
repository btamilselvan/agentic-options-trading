"""Session VWAP (requirements.md section 4.2's "Trend" feature family).

Definition: cumulative typical-price-weighted-by-volume over 1-minute
bars from the regular session open (09:30 America/New_York) through
`as_of`, reset every session. Typical price = (high+low+close)/3.
Premarket bars are explicitly excluded — VWAP resets at the regular
session open, not the extended-hours open. Returns None (never 0) when
no qualifying bar has both a price and a volume.
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from trading_app.schemas.market_data import Candle

MARKET_TZ = ZoneInfo("America/New_York")
SESSION_OPEN = time(9, 30)


def compute_session_vwap(bars: list[Candle], as_of: datetime) -> float | None:
    as_of_market = as_of.astimezone(MARKET_TZ)
    session_date = as_of_market.date()

    numerator = 0.0
    denominator = 0.0
    for bar in bars:
        bar_market = bar.market_timestamp.astimezone(MARKET_TZ)
        if bar_market.date() != session_date or bar_market.time() < SESSION_OPEN:
            continue
        if bar_market > as_of_market:
            continue
        if bar.high is None or bar.low is None or bar.close is None or bar.volume is None:
            continue
        typical_price = (bar.high + bar.low + bar.close) / 3
        numerator += typical_price * bar.volume
        denominator += bar.volume

    if denominator <= 0:
        return None
    return numerator / denominator
