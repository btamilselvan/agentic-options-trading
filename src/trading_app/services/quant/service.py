"""Quant-engine orchestration: fetch raw bars via MarketDataProvider,
then hand off to `engine.compute_feature_snapshot`. Provider I/O lives
here so `engine.py` stays pure/DB-free and independently testable.
"""
from __future__ import annotations

from uuid import UUID

from trading_app.config import QuantEngineSettings
from trading_app.schemas.features import FeatureSnapshot
from trading_app.schemas.market_data import Candle, Interval
from trading_app.services.market_data.base import MarketDataProvider
from trading_app.services.quant.engine import compute_feature_snapshot


async def _fetch_benchmark_data(
    provider: MarketDataProvider, symbols: list[str], cfg: QuantEngineSettings
) -> dict[str, tuple[list[Candle], float | None]]:
    result: dict[str, tuple[list[Candle], float | None]] = {}
    for symbol in symbols:
        minute_bars = await provider.get_candles(
            symbol,
            Interval.ONE_MIN,
            lookback_days=cfg.rvol_lookback_days,
            include_extended_hours=cfg.include_extended_hours,
        )
        daily_bars = await provider.get_candles(
            symbol, Interval.DAILY, lookback_days=cfg.daily_lookback_days
        )
        prior_close = daily_bars[-1].close if daily_bars else None
        result[symbol] = (minute_bars, prior_close)
    return result


async def compute_snapshots_for_candidates(
    candidates: list[tuple[str, UUID]],
    provider: MarketDataProvider,
    cfg: QuantEngineSettings,
) -> list[FeatureSnapshot]:
    """`candidates` is (symbol, correlation_id) pairs — the caller is
    responsible for sourcing these from the screener's persisted
    candidates so the correlation chain threads through end to end
    (requirements.md section 6)."""
    sector_symbols = {
        cfg.sector_etf_map[symbol] for symbol, _ in candidates if symbol in cfg.sector_etf_map
    }
    all_benchmark_symbols = list(dict.fromkeys([*cfg.benchmark_symbols, *sector_symbols]))
    benchmark_data = await _fetch_benchmark_data(provider, all_benchmark_symbols, cfg)

    snapshots = []
    for symbol, correlation_id in candidates:
        minute_bars = await provider.get_candles(
            symbol,
            Interval.ONE_MIN,
            lookback_days=cfg.rvol_lookback_days,
            include_extended_hours=cfg.include_extended_hours,
        )
        daily_bars = await provider.get_candles(
            symbol, Interval.DAILY, lookback_days=cfg.daily_lookback_days
        )
        snapshots.append(
            compute_feature_snapshot(
                symbol,
                minute_bars,
                daily_bars,
                benchmark_data,
                cfg,
                correlation_id=correlation_id,
            )
        )
    return snapshots
