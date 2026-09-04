from __future__ import annotations

from datetime import UTC, datetime

from trading_app.config import ScreenerSettings
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.base import MarketSnapshot
from trading_app.services.screener.filters import evaluate_filters
from trading_app.services.screener.metrics import compute_metrics
from trading_app.services.screener.scoring import score_symbol

_CFG = ScreenerSettings()


def _snapshot(**overrides) -> MarketSnapshot:
    defaults = dict(
        symbol="TEST",
        last_price=100.0,
        prior_close=95.0,  # +5.26% move
        session_volume=5_000_000.0,
        avg_volume_baseline=2_000_000.0,  # RVOL 2.5x
        bid=99.95,
        ask=100.05,  # ~0.1% spread
        options_available=True,
        market_timestamp=datetime(2026, 9, 3, 14, 30, tzinfo=UTC),
        source="test-fixture",
        freshness=DataFreshness.FRESH,
    )
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


def test_healthy_snapshot_passes_every_filter():
    snapshot = _snapshot()
    metrics = compute_metrics(snapshot)
    assert evaluate_filters(snapshot, metrics, _CFG) == []


def test_stale_data_fails():
    snapshot = _snapshot(freshness=DataFreshness.STALE)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("freshness" in f for f in failures)


def test_price_outside_range_fails():
    snapshot = _snapshot(last_price=1.0, prior_close=1.0)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("price" in f for f in failures)


def test_low_rvol_fails():
    snapshot = _snapshot(session_volume=100_000.0, avg_volume_baseline=2_000_000.0)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("RVOL" in f for f in failures)


def test_flat_move_fails():
    snapshot = _snapshot(last_price=100.0, prior_close=100.0)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("move" in f for f in failures)


def test_wide_spread_fails():
    snapshot = _snapshot(bid=90.0, ask=110.0)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("spread" in f for f in failures)


def test_missing_options_fails_when_required():
    snapshot = _snapshot(options_available=False)
    metrics = compute_metrics(snapshot)
    failures = evaluate_filters(snapshot, metrics, _CFG)
    assert any("options" in f for f in failures)


def test_missing_options_allowed_when_not_required():
    cfg = ScreenerSettings(require_options=False)
    snapshot = _snapshot(options_available=False)
    metrics = compute_metrics(snapshot)
    assert evaluate_filters(snapshot, metrics, cfg) == []


def test_score_rewards_higher_rvol_move_and_tighter_spread():
    weak = _snapshot(
        session_volume=2_200_000.0,  # RVOL ~1.1x
        prior_close=99.0,  # small move
        bid=99.90,
        ask=100.10,
    )
    strong = _snapshot(
        session_volume=8_000_000.0,  # RVOL 4x
        prior_close=90.0,  # big move
        bid=99.99,
        ask=100.01,  # tight spread
    )
    weak_score, _ = score_symbol(compute_metrics(weak), weak, _CFG)
    strong_score, _ = score_symbol(compute_metrics(strong), strong, _CFG)
    assert strong_score > weak_score
