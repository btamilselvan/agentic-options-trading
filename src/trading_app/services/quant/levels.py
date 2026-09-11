"""Level features (requirements.md section 4.2): previous-day H/L/C,
premarket H/L, opening-range H/L (configurable duration), session H/L.
America/New_York session boundaries throughout, matching VWAP/RVOL.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from trading_app.schemas.market_data import Candle
from trading_app.services.quant.vwap import MARKET_TZ, SESSION_OPEN


def compute_prev_day_levels(
    daily_bars: list[Candle],
) -> tuple[float | None, float | None, float | None]:
    """`daily_bars` must exclude today's (not-yet-closed) bar — the
    provider is responsible for that, not this function. Returns
    (high, low, close) of the most recent bar, oldest-first input."""
    if not daily_bars:
        return None, None, None
    last = daily_bars[-1]
    return last.high, last.low, last.close


def compute_premarket_levels(
    bars: list[Candle], as_of: datetime
) -> tuple[float | None, float | None]:
    as_of_market = as_of.astimezone(MARKET_TZ)
    today = as_of_market.date()
    highs = []
    lows = []
    for bar in bars:
        bar_market = bar.market_timestamp.astimezone(MARKET_TZ)
        if bar_market.date() != today or bar_market.time() >= SESSION_OPEN:
            continue
        if bar.high is not None:
            highs.append(bar.high)
        if bar.low is not None:
            lows.append(bar.low)
    return (max(highs) if highs else None, min(lows) if lows else None)


def compute_opening_range(
    bars: list[Candle], as_of: datetime, duration_minutes: int
) -> tuple[float | None, float | None]:
    as_of_market = as_of.astimezone(MARKET_TZ)
    today = as_of_market.date()
    session_open = datetime.combine(today, SESSION_OPEN, tzinfo=MARKET_TZ)
    window_end = session_open + timedelta(minutes=duration_minutes)
    highs = []
    lows = []
    for bar in bars:
        bar_market = bar.market_timestamp.astimezone(MARKET_TZ)
        if bar_market.date() != today or not (session_open <= bar_market < window_end):
            continue
        if bar.high is not None:
            highs.append(bar.high)
        if bar.low is not None:
            lows.append(bar.low)
    return (max(highs) if highs else None, min(lows) if lows else None)


def compute_session_levels(
    bars: list[Candle], as_of: datetime
) -> tuple[float | None, float | None]:
    as_of_market = as_of.astimezone(MARKET_TZ)
    today = as_of_market.date()
    highs = []
    lows = []
    for bar in bars:
        bar_market = bar.market_timestamp.astimezone(MARKET_TZ)
        if bar_market.date() != today or bar_market.time() < SESSION_OPEN:
            continue
        if bar_market > as_of_market:
            continue
        if bar.high is not None:
            highs.append(bar.high)
        if bar.low is not None:
            lows.append(bar.low)
    return (max(highs) if highs else None, min(lows) if lows else None)
