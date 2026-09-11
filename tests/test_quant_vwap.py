from __future__ import annotations

from datetime import datetime

from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.quant.vwap import MARKET_TZ, compute_session_vwap


def _bar(hour: int, minute: int, *, high: float, low: float, close: float, volume: float) -> Candle:
    return Candle(
        symbol="TEST",
        interval=Interval.ONE_MIN,
        high=high,
        low=low,
        close=close,
        volume=volume,
        market_timestamp=datetime(2026, 9, 3, hour, minute, tzinfo=MARKET_TZ),
        source="test-fixture",
    )


def test_vwap_hand_computed():
    # typical price = (h+l+c)/3
    # bar1 09:30: typical=(10+8+9)/3=9.0, vol=100  -> num=900,  denom=100
    # bar2 09:31: typical=(12+10+11)/3=11.0, vol=200 -> num=2200, denom=200
    # vwap = (900+2200)/(100+200) = 3100/300 = 10.3333
    bars = [
        _bar(9, 30, high=10, low=8, close=9, volume=100),
        _bar(9, 31, high=12, low=10, close=11, volume=200),
    ]
    as_of = datetime(2026, 9, 3, 9, 31, tzinfo=MARKET_TZ)
    vwap = compute_session_vwap(bars, as_of)
    assert vwap is not None
    assert abs(vwap - 10.3333) < 0.001


def test_vwap_excludes_premarket_bars():
    bars = [
        _bar(9, 0, high=100, low=100, close=100, volume=1_000_000),  # premarket, excluded
        _bar(9, 30, high=10, low=8, close=9, volume=100),
    ]
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    vwap = compute_session_vwap(bars, as_of)
    assert vwap == 9.0  # only the regular-session bar counts


def test_vwap_excludes_bars_after_as_of():
    bars = [
        _bar(9, 30, high=10, low=8, close=9, volume=100),
        _bar(9, 45, high=1000, low=1000, close=1000, volume=1_000_000),  # in the future
    ]
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    vwap = compute_session_vwap(bars, as_of)
    assert vwap == 9.0


def test_vwap_none_when_no_qualifying_bars():
    as_of = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)
    assert compute_session_vwap([], as_of) is None
