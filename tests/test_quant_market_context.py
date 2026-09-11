from __future__ import annotations

from datetime import datetime, timedelta

from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.quant.market_context import compute_benchmark_context
from trading_app.services.quant.vwap import MARKET_TZ

_SESSION_OPEN = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)


def _bars(closes: list[float]) -> list[Candle]:
    return [
        Candle(
            symbol="BENCH",
            interval=Interval.ONE_MIN,
            high=c,
            low=c,
            close=c,
            volume=100.0,
            market_timestamp=_SESSION_OPEN + timedelta(minutes=i),
            source="test-fixture",
        )
        for i, c in enumerate(closes)
    ]


def test_benchmark_trend_and_pct_move():
    # Uptrend closes -> ema20 rises above ema50 given enough bars; use a
    # short window so both EMA periods are computable with few bars.
    closes = [float(100 + i) for i in range(60)]  # 100..159, steadily rising
    as_of = _SESSION_OPEN + timedelta(minutes=len(closes) - 1)
    context = compute_benchmark_context(
        {"SPY": (_bars(closes), 90.0)}, as_of, ema_fast_period=5, ema_slow_period=10
    )
    assert context.trend_by_symbol["SPY"] == "bullish"
    # price=159, prior_close=90 -> pct move = (159-90)/90*100
    assert context.pct_move_by_symbol["SPY"] is not None
    assert abs(context.pct_move_by_symbol["SPY"] - ((159 - 90) / 90 * 100)) < 0.01


def test_benchmark_pct_move_none_without_prior_close():
    as_of = datetime(2026, 9, 3, 9, 31, tzinfo=MARKET_TZ)
    context = compute_benchmark_context({"SPY": (_bars([100.0, 101.0]), None)}, as_of)
    assert context.pct_move_by_symbol["SPY"] is None


def test_benchmark_trend_range_when_insufficient_history():
    as_of = datetime(2026, 9, 3, 9, 31, tzinfo=MARKET_TZ)
    context = compute_benchmark_context(
        {"SPY": (_bars([100.0, 101.0]), 90.0)}, as_of, ema_fast_period=20, ema_slow_period=50
    )
    assert context.trend_by_symbol["SPY"] == "range"
