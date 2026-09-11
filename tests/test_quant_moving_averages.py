from __future__ import annotations

from trading_app.services.quant.moving_averages import (
    classify_ema_alignment,
    classify_trend,
    compute_ema,
    compute_ema_series,
    compute_ema_slope,
)


def test_ema_insufficient_history_returns_none():
    assert compute_ema([1.0, 2.0], period=5) is None
    assert compute_ema_series([1.0, 2.0], period=5) == [None, None]


def test_ema_seeds_with_sma_then_recurses():
    # period=3, closes=[10, 11, 12, 13]
    # seed (SMA of first 3) = (10+11+12)/3 = 11.0
    # alpha = 2/(3+1) = 0.5
    # next EMA = 13*0.5 + 11.0*0.5 = 6.5 + 5.5 = 12.0
    closes = [10.0, 11.0, 12.0, 13.0]
    series = compute_ema_series(closes, period=3)
    assert series[:2] == [None, None]
    assert series[2] == 11.0
    assert series[3] == 12.0
    assert compute_ema(closes, period=3) == 12.0


def test_ema_slope_is_difference_between_last_two_values():
    closes = [10.0, 11.0, 12.0, 13.0]
    # series = [None, None, 11.0, 12.0] -> slope = 12.0 - 11.0 = 1.0
    assert compute_ema_slope(closes, period=3) == 1.0


def test_ema_slope_none_when_insufficient_history():
    assert compute_ema_slope([10.0, 11.0], period=3) is None


def test_classify_trend_bullish():
    assert classify_trend(ema_fast=20.0, ema_slow=10.0, price=25.0, vwap=15.0) == "bullish"


def test_classify_trend_bearish():
    assert classify_trend(ema_fast=10.0, ema_slow=20.0, price=15.0, vwap=25.0) == "bearish"


def test_classify_trend_range_on_mixed_signal():
    assert classify_trend(ema_fast=20.0, ema_slow=10.0, price=15.0, vwap=25.0) == "range"


def test_classify_trend_range_when_missing_data():
    assert classify_trend(None, 10.0, 15.0, 25.0) == "range"


def test_classify_ema_alignment_bullish():
    assert classify_ema_alignment(ema_9=30.0, ema_20=20.0, ema_50=10.0) == 1.0


def test_classify_ema_alignment_bearish():
    assert classify_ema_alignment(ema_9=10.0, ema_20=20.0, ema_50=30.0) == -1.0


def test_classify_ema_alignment_mixed():
    assert classify_ema_alignment(ema_9=20.0, ema_20=30.0, ema_50=10.0) == 0.0


def test_classify_ema_alignment_none_when_missing():
    assert classify_ema_alignment(None, 20.0, 10.0) is None
