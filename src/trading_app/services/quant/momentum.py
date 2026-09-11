"""Momentum features (requirements.md section 4.2): RSI, ROC — both
period-configurable per QuantEngineSettings.

RSI uses Wilder's original smoothing (average gain/loss smoothed the
same way as ATR, not a plain SMA) — the standard, most common RSI
definition. ROC is a simple percent change over `period` bars back.
"""
from __future__ import annotations


def compute_rsi(closes: list[float], period: int) -> float | None:
    if len(closes) < period + 1:
        return None

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_roc(closes: list[float], period: int) -> float | None:
    if len(closes) <= period:
        return None
    reference = closes[-1 - period]
    if reference == 0:
        return None
    return (closes[-1] - reference) / reference * 100
