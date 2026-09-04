"""Screener ranking (requirements.md section 4.1): "favor liquid symbols
with active options and meaningful intraday movement." Weights are
configuration (`ScreenerSettings`), never code constants.
"""
from __future__ import annotations

from trading_app.config import ScreenerSettings
from trading_app.services.market_data.base import MarketSnapshot
from trading_app.services.screener.metrics import ScreenerMetrics


def score_symbol(
    metrics: ScreenerMetrics, snapshot: MarketSnapshot, cfg: ScreenerSettings
) -> tuple[float, list[str]]:
    """Only called for symbols that already passed `evaluate_filters` —
    this ranks survivors, it doesn't gate them."""
    reasons: list[str] = []
    score = 0.0

    score += cfg.weight_rvol * metrics.rvol
    reasons.append(f"RVOL {metrics.rvol:.2f}x")

    score += cfg.weight_move * abs(metrics.move_pct) * 100
    reasons.append(f"move {metrics.move_pct:+.2%}")

    if metrics.spread_pct is not None:
        tightness = max(0.0, cfg.max_spread_pct - metrics.spread_pct)
        score += cfg.weight_spread * tightness * 100
        reasons.append(f"spread {metrics.spread_pct:.3%}")

    if snapshot.options_available:
        score += cfg.weight_options_bonus
        reasons.append("options available")

    return score, reasons
