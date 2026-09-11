"""Quantitative engine entry point (requirements.md section 4.2):
assembles a versioned FeatureSnapshot for one symbol from raw bar
history. Pure/DB-free — persistence lives in
`trading_app.db.repositories.features`; fetching the bars this consumes
is `MarketDataProvider.get_candles` (see `workers/quant_worker.py` for
the orchestration that ties fetch -> compute -> persist together).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from trading_app.config import QuantEngineSettings
from trading_app.schemas.common import utcnow
from trading_app.schemas.features import FeatureSnapshot
from trading_app.schemas.market_data import Candle, DataFreshness
from trading_app.services.quant.levels import (
    compute_opening_range,
    compute_premarket_levels,
    compute_prev_day_levels,
    compute_session_levels,
)
from trading_app.services.quant.market_context import compute_benchmark_context
from trading_app.services.quant.momentum import compute_roc, compute_rsi
from trading_app.services.quant.moving_averages import (
    classify_ema_alignment,
    compute_ema,
    compute_ema_slope,
)
from trading_app.services.quant.volatility import compute_atr, compute_atr_pct
from trading_app.services.quant.volume import (
    compute_avg_daily_volume,
    compute_rvol,
    compute_volume_acceleration,
)
from trading_app.services.quant.vwap import compute_session_vwap


def _pct_distance(value: float | None, reference: float | None) -> float | None:
    if value is None or reference is None or reference == 0:
        return None
    return (value - reference) / reference * 100


def _relative_move(own_pct_move: float | None, benchmark_pct_move: float | None) -> float | None:
    if own_pct_move is None or benchmark_pct_move is None:
        return None
    return own_pct_move - benchmark_pct_move


def compute_feature_snapshot(
    symbol: str,
    minute_bars: list[Candle],
    daily_bars: list[Candle],
    benchmark_data: dict[str, tuple[list[Candle], float | None]],
    cfg: QuantEngineSettings,
    *,
    as_of: datetime | None = None,
    correlation_id: UUID | None = None,
    data_quality: DataFreshness = DataFreshness.FRESH,
) -> FeatureSnapshot:
    as_of = as_of or utcnow()
    closes = [bar.close for bar in minute_bars if bar.close is not None]
    price = closes[-1] if closes else None
    vwap = compute_session_vwap(minute_bars, as_of)

    ema_by_period = {period: compute_ema(closes, period) for period in cfg.ema_periods}
    ema_slope_by_period = {period: compute_ema_slope(closes, period) for period in cfg.ema_periods}
    ema_9, ema_20, ema_50 = (ema_by_period.get(period) for period in (9, 20, 50))

    atr = compute_atr(minute_bars, cfg.atr_period)
    prev_high, prev_low, prev_close = compute_prev_day_levels(daily_bars)
    premarket_high, premarket_low = compute_premarket_levels(minute_bars, as_of)
    opening_high, opening_low = compute_opening_range(minute_bars, as_of, cfg.opening_range_minutes)
    session_high, session_low = compute_session_levels(minute_bars, as_of)

    features: dict[str, float | None] = {
        "vwap": vwap,
        "ema_9": ema_9,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_9_slope": ema_slope_by_period.get(9),
        "ema_20_slope": ema_slope_by_period.get(20),
        "ema_50_slope": ema_slope_by_period.get(50),
        "price_dist_from_vwap_pct": _pct_distance(price, vwap),
        "price_dist_from_ema20_pct": _pct_distance(price, ema_20),
        "ema_alignment": classify_ema_alignment(ema_9, ema_20, ema_50),
        "rsi": compute_rsi(closes, cfg.rsi_period),
        "roc": compute_roc(closes, cfg.roc_period),
        "atr": atr,
        "atr_pct": compute_atr_pct(atr, price),
        "rvol": compute_rvol(minute_bars, as_of),
        "volume_acceleration": compute_volume_acceleration(
            minute_bars, cfg.volume_acceleration_window
        ),
        "avg_daily_volume": compute_avg_daily_volume(daily_bars),
        "prev_day_high": prev_high,
        "prev_day_low": prev_low,
        "prev_day_close": prev_close,
        "premarket_high": premarket_high,
        "premarket_low": premarket_low,
        "opening_range_high": opening_high,
        "opening_range_low": opening_low,
        "session_high": session_high,
        "session_low": session_low,
    }

    benchmark_context = compute_benchmark_context(benchmark_data, as_of)
    sector_etf_symbol = cfg.sector_etf_map.get(symbol)
    own_pct_move = _pct_distance(price, prev_close)
    market_context: dict[str, float | str | None] = {
        "spy_trend": benchmark_context.trend_by_symbol.get("SPY"),
        "qqq_trend": benchmark_context.trend_by_symbol.get("QQQ"),
        "sector_etf_symbol": sector_etf_symbol,
        "sector_trend": (
            benchmark_context.trend_by_symbol.get(sector_etf_symbol) if sector_etf_symbol else None
        ),
        "relative_move_vs_spy_pct": _relative_move(
            own_pct_move, benchmark_context.pct_move_by_symbol.get("SPY")
        ),
        "relative_move_vs_qqq_pct": _relative_move(
            own_pct_move, benchmark_context.pct_move_by_symbol.get("QQQ")
        ),
    }

    kwargs: dict = dict(
        symbol=symbol,
        as_of=as_of,
        feature_definition_version=cfg.feature_definition_version,
        features=features,
        market_context=market_context,
        data_quality=data_quality,
    )
    if correlation_id is not None:
        kwargs["correlation_id"] = correlation_id
    return FeatureSnapshot(**kwargs)
