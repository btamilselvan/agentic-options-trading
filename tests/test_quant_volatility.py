from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.quant.volatility import compute_atr, compute_atr_pct, compute_true_ranges

_START = datetime(2026, 9, 3, 14, 30, tzinfo=UTC)


def _bar(i: int, *, high: float | None, low: float | None, close: float | None) -> Candle:
    return Candle(
        symbol="TEST",
        interval=Interval.ONE_MIN,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
        market_timestamp=_START + timedelta(minutes=i),
        source="test-fixture",
    )


# Hand-computed: TR = max(h-l, |h-prev_close|, |l-prev_close|)
# b1 close=10 (no TR, no previous close)
# b2 h=11 l=9  close=10 prev_close=10 -> TR = max(2, 1, 1) = 2
# b3 h=12 l=10 close=11 prev_close=10 -> TR = max(2, 2, 0) = 2
# b4 h=13 l=11 close=12 prev_close=11 -> TR = max(2, 2, 0) = 2
# b5 h=10 l=8  close=9  prev_close=12 -> TR = max(2, 2, 4) = 4
_BARS = [
    _bar(0, high=10, low=10, close=10),
    _bar(1, high=11, low=9, close=10),
    _bar(2, high=12, low=10, close=11),
    _bar(3, high=13, low=11, close=12),
    _bar(4, high=10, low=8, close=9),
]


def test_true_ranges_hand_computed():
    trs = compute_true_ranges(_BARS)
    assert trs == [None, 2, 2, 2, 4]


def test_atr_hand_computed():
    # period=3: seed = avg(2,2,2) = 2.0; next tr=4 -> (2.0*2+4)/3 = 2.66667
    atr = compute_atr(_BARS, period=3)
    assert atr is not None
    assert abs(atr - 2.66667) < 0.001


def test_atr_insufficient_history_returns_none():
    assert compute_atr(_BARS, period=10) is None


def test_atr_pct():
    assert compute_atr_pct(atr=5.0, price=100.0) == 5.0
    assert compute_atr_pct(atr=None, price=100.0) is None
    assert compute_atr_pct(atr=5.0, price=None) is None
