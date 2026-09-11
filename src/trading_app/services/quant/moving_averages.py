"""EMA trend features (requirements.md section 4.2's "Trend" family):
EMA(9/20/50), each's slope, and alignment/trend classification.

EMA seeding convention: the first `period` closes seed via SMA, then the
standard recursive EMA (alpha = 2/(period+1)) applies to the rest. Fewer
than `period` closes returns None throughout — never a fabricated value
from insufficient history.
"""
from __future__ import annotations


def compute_ema_series(closes: list[float], period: int) -> list[float | None]:
    """One EMA value per input close, aligned by index; the first
    `period - 1` entries are None (insufficient history to seed)."""
    if len(closes) < period:
        return [None] * len(closes)

    result: list[float | None] = [None] * (period - 1)
    ema = sum(closes[:period]) / period
    result.append(ema)
    alpha = 2 / (period + 1)
    for close in closes[period:]:
        ema = close * alpha + ema * (1 - alpha)
        result.append(ema)
    return result


def compute_ema(closes: list[float], period: int) -> float | None:
    series = compute_ema_series(closes, period)
    return series[-1] if series else None


def compute_ema_slope(closes: list[float], period: int) -> float | None:
    series = compute_ema_series(closes, period)
    if len(series) < 2 or series[-1] is None or series[-2] is None:
        return None
    return series[-1] - series[-2]


def classify_trend(
    ema_fast: float | None, ema_slow: float | None, price: float | None, vwap: float | None
) -> str:
    """"bullish" when the fast EMA leads the slow one and price is above
    VWAP; "bearish" for the inverse; "range" for mixed or missing
    signals. Used both for this symbol's own trend and, with a
    benchmark/sector ETF's own EMAs, for market_context."""
    if ema_fast is None or ema_slow is None or price is None or vwap is None:
        return "range"
    if ema_fast > ema_slow and price > vwap:
        return "bullish"
    if ema_fast < ema_slow and price < vwap:
        return "bearish"
    return "range"


def classify_ema_alignment(
    ema_9: float | None, ema_20: float | None, ema_50: float | None
) -> float | None:
    """Full 3-way EMA(9/20/50) ordering, numeric-coded for the
    FeatureSnapshot.features float-only dict: 1.0 bullish-aligned
    (9 > 20 > 50), -1.0 bearish-aligned (9 < 20 < 50), 0.0 mixed."""
    if ema_9 is None or ema_20 is None or ema_50 is None:
        return None
    if ema_9 > ema_20 > ema_50:
        return 1.0
    if ema_9 < ema_20 < ema_50:
        return -1.0
    return 0.0
