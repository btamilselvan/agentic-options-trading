"""Market-context features (requirements.md section 4.2): SPY/QQQ
trend/state, mapped sector-ETF trend/state, relative movement vs each
benchmark. Reuses `moving_averages.classify_trend` — the same
classifier that produces this symbol's own trend, applied to each
benchmark/sector symbol's own EMAs/VWAP/price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from trading_app.schemas.market_data import Candle
from trading_app.services.quant.moving_averages import classify_trend, compute_ema
from trading_app.services.quant.vwap import compute_session_vwap


@dataclass(frozen=True)
class BenchmarkContext:
    trend_by_symbol: dict[str, str] = field(default_factory=dict)
    pct_move_by_symbol: dict[str, float | None] = field(default_factory=dict)


def compute_benchmark_context(
    benchmark_data: dict[str, tuple[list[Candle], float | None]],
    as_of: datetime,
    *,
    ema_fast_period: int = 20,
    ema_slow_period: int = 50,
) -> BenchmarkContext:
    """`benchmark_data` maps a symbol (e.g. "SPY", or a mapped sector
    ETF like "XLK") to its own (minute_bars, prior_day_close)."""
    trend_by_symbol: dict[str, str] = {}
    pct_move_by_symbol: dict[str, float | None] = {}

    for symbol, (bars, prior_close) in benchmark_data.items():
        closes = [b.close for b in bars if b.close is not None]
        price = closes[-1] if closes else None
        vwap = compute_session_vwap(bars, as_of)
        ema_fast = compute_ema(closes, ema_fast_period)
        ema_slow = compute_ema(closes, ema_slow_period)
        trend_by_symbol[symbol] = classify_trend(ema_fast, ema_slow, price, vwap)

        if price is not None and prior_close:
            pct_move_by_symbol[symbol] = (price - prior_close) / prior_close * 100
        else:
            pct_move_by_symbol[symbol] = None

    return BenchmarkContext(trend_by_symbol=trend_by_symbol, pct_move_by_symbol=pct_move_by_symbol)
