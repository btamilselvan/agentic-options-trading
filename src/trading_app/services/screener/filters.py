"""Deterministic screener filters (requirements.md section 4.1): price,
intraday volume, relative volume, percentage move, spread/liquidity
proxy, and options availability. Every threshold comes from
`ScreenerSettings` — never a code constant.
"""
from __future__ import annotations

from trading_app.config import ScreenerSettings
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.base import MarketSnapshot
from trading_app.services.screener.metrics import ScreenerMetrics


def evaluate_filters(
    snapshot: MarketSnapshot, metrics: ScreenerMetrics, cfg: ScreenerSettings
) -> list[str]:
    """Returns failure reasons; an empty list means the symbol passes
    every filter. Never trades a fabricated value for a missing one —
    missing/stale inputs are filter failures, not defaults."""
    failures: list[str] = []

    if snapshot.freshness != DataFreshness.FRESH:
        failures.append(f"data freshness is {snapshot.freshness.value}, not FRESH")

    if snapshot.last_price is None or not (cfg.min_price <= snapshot.last_price <= cfg.max_price):
        failures.append(
            f"price {snapshot.last_price} outside configured [{cfg.min_price}, {cfg.max_price}]"
        )

    if snapshot.session_volume is None or snapshot.session_volume < cfg.min_session_volume:
        failures.append(
            f"session volume {snapshot.session_volume} below minimum {cfg.min_session_volume}"
        )

    if metrics.rvol < cfg.min_rvol:
        failures.append(f"RVOL {metrics.rvol:.2f}x below minimum {cfg.min_rvol:.2f}x")

    if abs(metrics.move_pct) < cfg.min_abs_percent_move:
        failures.append(
            f"move {metrics.move_pct:+.2%} below minimum {cfg.min_abs_percent_move:.2%}"
        )

    if metrics.spread_pct is None:
        failures.append("no valid bid/ask to compute spread")
    elif metrics.spread_pct > cfg.max_spread_pct:
        failures.append(f"spread {metrics.spread_pct:.3%} exceeds maximum {cfg.max_spread_pct:.3%}")

    if cfg.require_options and not snapshot.options_available:
        failures.append("no options available")

    return failures
