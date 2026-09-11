"""Volume features (requirements.md section 4.2): canonical,
time-of-day-aligned RVOL, volume acceleration, rolling average daily
volume.

RVOL definition: today's regular-session cumulative volume through
`as_of` divided by the average cumulative volume at the same
elapsed-minutes-since-open across the other sessions present in `bars`
— a proper time-of-day comparison, distinct from (and more correct
than) the screener's cheap session-total proxy in
`services.screener.metrics`. Regular session only; premarket volume is
excluded from this specific calculation, matching VWAP's convention.
"""
from __future__ import annotations

from datetime import date, datetime

from trading_app.schemas.market_data import Candle
from trading_app.services.quant.vwap import MARKET_TZ, SESSION_OPEN


def compute_rvol(bars: list[Candle], as_of: datetime) -> float | None:
    as_of_market = as_of.astimezone(MARKET_TZ)
    today = as_of_market.date()

    by_day: dict[date, list[tuple[int, float]]] = {}
    for bar in bars:
        bar_market = bar.market_timestamp.astimezone(MARKET_TZ)
        if bar_market.time() < SESSION_OPEN or bar.volume is None:
            continue
        session_open = datetime.combine(bar_market.date(), SESSION_OPEN, tzinfo=MARKET_TZ)
        elapsed_minutes = int((bar_market - session_open).total_seconds() // 60)
        by_day.setdefault(bar_market.date(), []).append((elapsed_minutes, bar.volume))

    if today not in by_day:
        return None
    today_session_open = datetime.combine(today, SESSION_OPEN, tzinfo=MARKET_TZ)
    today_elapsed = int((as_of_market - today_session_open).total_seconds() // 60)
    today_cume = sum(v for elapsed, v in by_day[today] if elapsed <= today_elapsed)

    baselines = [
        sum(v for elapsed, v in entries if elapsed <= today_elapsed)
        for day, entries in by_day.items()
        if day != today
    ]
    baselines = [b for b in baselines if b > 0]
    if not baselines:
        return None

    avg_baseline = sum(baselines) / len(baselines)
    if avg_baseline <= 0:
        return None
    return today_cume / avg_baseline


def compute_volume_acceleration(bars: list[Candle], window: int) -> float | None:
    """Ratio of the most recent `window` bars' volume to the `window`
    bars immediately before that."""
    volumes = [b.volume for b in bars if b.volume is not None]
    if len(volumes) < window * 2:
        return None
    recent = sum(volumes[-window:])
    prior = sum(volumes[-2 * window : -window])
    if prior <= 0:
        return None
    return recent / prior


def compute_avg_daily_volume(daily_bars: list[Candle]) -> float | None:
    volumes = [b.volume for b in daily_bars if b.volume is not None]
    if not volumes:
        return None
    return sum(volumes) / len(volumes)
