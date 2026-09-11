"""Volatility features (requirements.md section 4.2): ATR + ATR%.

True range per bar: max(high-low, |high-prev_close|, |low-prev_close|).
ATR uses the same Wilder smoothing as RSI's average gain/loss.
"""
from __future__ import annotations

from trading_app.schemas.market_data import Candle


def compute_true_ranges(bars: list[Candle]) -> list[float | None]:
    """One true range per bar; the first bar is always None (no previous
    close to compare against)."""
    trs: list[float | None] = []
    prev_close: float | None = None
    for bar in bars:
        if prev_close is None or bar.high is None or bar.low is None:
            trs.append(None)
        else:
            trs.append(
                max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close))
            )
        prev_close = bar.close
    return trs


def compute_atr(bars: list[Candle], period: int) -> float | None:
    true_ranges = [tr for tr in compute_true_ranges(bars) if tr is not None]
    if len(true_ranges) < period:
        return None
    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def compute_atr_pct(atr: float | None, price: float | None) -> float | None:
    if atr is None or price is None or price == 0:
        return None
    return atr / price * 100
