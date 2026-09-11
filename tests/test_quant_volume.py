from __future__ import annotations

from datetime import datetime

from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.quant.volume import (
    compute_avg_daily_volume,
    compute_rvol,
    compute_volume_acceleration,
)
from trading_app.services.quant.vwap import MARKET_TZ


def _bar(day: int, hour: int, minute: int, volume: float) -> Candle:
    return Candle(
        symbol="TEST",
        interval=Interval.ONE_MIN,
        close=100.0,
        volume=volume,
        market_timestamp=datetime(2026, 9, day, hour, minute, tzinfo=MARKET_TZ),
        source="test-fixture",
    )


def test_rvol_hand_computed():
    # Two prior sessions (Sep 1, Sep 2) each with bars at elapsed 0 and 5
    # minutes since open; today (Sep 3) same. Cumulative volume through
    # elapsed=5 each day:
    #   Sep 1: 100 + 100 = 200
    #   Sep 2: 200 + 200 = 400
    #   baseline avg = (200 + 400) / 2 = 300
    #   today:  225 + 225 = 450
    #   rvol = 450 / 300 = 1.5
    bars = [
        _bar(1, 9, 30, 100),
        _bar(1, 9, 35, 100),
        _bar(2, 9, 30, 200),
        _bar(2, 9, 35, 200),
        _bar(3, 9, 30, 225),
        _bar(3, 9, 35, 225),
    ]
    as_of = datetime(2026, 9, 3, 9, 35, tzinfo=MARKET_TZ)
    rvol = compute_rvol(bars, as_of)
    assert rvol is not None
    assert abs(rvol - 1.5) < 0.0001


def test_rvol_none_without_prior_sessions():
    bars = [_bar(3, 9, 30, 225)]
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    assert compute_rvol(bars, as_of) is None


def test_rvol_excludes_premarket_volume():
    bars = [
        _bar(1, 8, 0, 999_999),  # premarket on the baseline day, excluded
        _bar(1, 9, 30, 100),
        _bar(3, 9, 30, 100),
    ]
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    rvol = compute_rvol(bars, as_of)
    assert rvol == 1.0


def test_volume_acceleration_hand_computed():
    volumes = [100.0, 100.0, 100.0, 200.0, 200.0, 200.0]  # window=3
    bars = [
        Candle(
            symbol="TEST",
            interval=Interval.ONE_MIN,
            close=1.0,
            volume=v,
            market_timestamp=datetime(2026, 9, 3, 9, 30 + i, tzinfo=MARKET_TZ),
            source="test-fixture",
        )
        for i, v in enumerate(volumes)
    ]
    # recent 3 = 200+200+200 = 600; prior 3 = 100+100+100 = 300 -> 2.0
    assert compute_volume_acceleration(bars, window=3) == 2.0


def test_volume_acceleration_none_when_insufficient_bars():
    bars = [
        Candle(
            symbol="TEST",
            interval=Interval.ONE_MIN,
            close=1.0,
            volume=100.0,
            market_timestamp=datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ),
            source="test-fixture",
        )
    ]
    assert compute_volume_acceleration(bars, window=3) is None


def test_avg_daily_volume():
    daily_bars = [
        Candle(
            symbol="TEST",
            interval=Interval.DAILY,
            close=1.0,
            volume=v,
            market_timestamp=datetime(2026, 9, d, 16, 0, tzinfo=MARKET_TZ),
            source="test-fixture",
        )
        for d, v in [(1, 100.0), (2, 200.0), (3, 300.0)]
    ]
    assert compute_avg_daily_volume(daily_bars) == 200.0


def test_avg_daily_volume_none_when_empty():
    assert compute_avg_daily_volume([]) is None
