"""Derived metrics shared by the screener's filters and scoring, so the
two never compute rvol/move/spread differently from each other."""
from __future__ import annotations

from dataclasses import dataclass

from trading_app.services.market_data.base import MarketSnapshot


@dataclass(frozen=True)
class ScreenerMetrics:
    # Cheap screener-level proxy — NOT the canonical, time-of-day-aligned
    # RVOL feature the quantitative engine (component 2) will compute.
    rvol: float
    move_pct: float
    spread_pct: float | None


def compute_metrics(snapshot: MarketSnapshot) -> ScreenerMetrics:
    rvol = (
        snapshot.session_volume / snapshot.avg_volume_baseline
        if snapshot.session_volume is not None and snapshot.avg_volume_baseline
        else 0.0
    )
    move_pct = (
        (snapshot.last_price - snapshot.prior_close) / snapshot.prior_close
        if snapshot.last_price is not None and snapshot.prior_close
        else 0.0
    )
    spread_pct = None
    if snapshot.bid is not None and snapshot.ask is not None and snapshot.ask > snapshot.bid >= 0:
        mid = (snapshot.bid + snapshot.ask) / 2
        if mid > 0:
            spread_pct = (snapshot.ask - snapshot.bid) / mid
    return ScreenerMetrics(rvol=rvol, move_pct=move_pct, spread_pct=spread_pct)
