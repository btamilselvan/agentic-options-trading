from __future__ import annotations

from datetime import datetime

from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.quant.levels import (
    compute_opening_range,
    compute_premarket_levels,
    compute_prev_day_levels,
    compute_session_levels,
)
from trading_app.services.quant.vwap import MARKET_TZ


def _bar(hour: int, minute: int, high: float, low: float) -> Candle:
    return Candle(
        symbol="TEST",
        interval=Interval.ONE_MIN,
        high=high,
        low=low,
        close=(high + low) / 2,
        volume=100.0,
        market_timestamp=datetime(2026, 9, 3, hour, minute, tzinfo=MARKET_TZ),
        source="test-fixture",
    )


def test_prev_day_levels_is_the_last_daily_bar():
    daily_bars = [
        Candle(
            symbol="TEST",
            interval=Interval.DAILY,
            high=110.0,
            low=90.0,
            close=100.0,
            volume=1.0,
            market_timestamp=datetime(2026, 9, 2, 16, 0, tzinfo=MARKET_TZ),
            source="test-fixture",
        )
    ]
    high, low, close = compute_prev_day_levels(daily_bars)
    assert (high, low, close) == (110.0, 90.0, 100.0)


def test_prev_day_levels_none_when_empty():
    assert compute_prev_day_levels([]) == (None, None, None)


def test_premarket_levels_excludes_regular_session():
    bars = [
        _bar(8, 0, high=50, low=40),
        _bar(8, 30, high=55, low=42),
        _bar(9, 30, high=200, low=190),  # regular session, excluded
    ]
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    high, low = compute_premarket_levels(bars, as_of)
    assert (high, low) == (55, 40)


def test_opening_range_respects_configured_duration():
    bars = [
        _bar(9, 30, high=10, low=8),
        _bar(9, 40, high=12, low=9),
        _bar(9, 50, high=20, low=19),  # outside a 15-minute opening range
    ]
    as_of = datetime(2026, 9, 3, 9, 50, tzinfo=MARKET_TZ)
    high, low = compute_opening_range(bars, as_of, duration_minutes=15)
    assert (high, low) == (12, 8)


def test_session_levels_excludes_bars_after_as_of():
    bars = [
        _bar(9, 30, high=10, low=8),
        _bar(9, 40, high=12, low=9),
        _bar(9, 50, high=20, low=19),
        _bar(9, 55, high=1000, low=1000),  # after as_of
    ]
    as_of = datetime(2026, 9, 3, 9, 50, tzinfo=MARKET_TZ)
    high, low = compute_session_levels(bars, as_of)
    assert (high, low) == (20, 8)
