from __future__ import annotations

from datetime import UTC, datetime

from trading_app.config import ScreenerSettings
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.base import MarketSnapshot
from trading_app.services.screener.service import run_screen

_NOW = datetime(2026, 9, 3, 14, 30, tzinfo=UTC)


class _FakeMarketDataProvider:
    def __init__(self, snapshots: dict[str, MarketSnapshot]) -> None:
        self._snapshots = snapshots

    async def get_market_snapshots(self, symbols: list[str]) -> list[MarketSnapshot]:
        return [self._snapshots[s] for s in symbols if s in self._snapshots]


class _FakeUniverseProvider:
    def __init__(self, symbols: list[str]) -> None:
        self._symbols = symbols

    async def discover_symbols(self) -> list[str]:
        return self._symbols


def _snapshot(symbol: str, **overrides) -> MarketSnapshot:
    defaults = dict(
        symbol=symbol,
        last_price=100.0,
        prior_close=95.0,
        session_volume=5_000_000.0,
        avg_volume_baseline=2_000_000.0,
        bid=99.95,
        ask=100.05,
        options_available=True,
        market_timestamp=_NOW,
        source="test-fixture",
        freshness=DataFreshness.FRESH,
    )
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


async def test_run_screen_filters_ranks_and_bounds_candidates():
    settings = ScreenerSettings(exclusions=["EXCLUDED"], max_candidates=10)
    market_data_provider = _FakeMarketDataProvider(
        {
            "GOOD": _snapshot("GOOD"),
            "BAD": _snapshot("BAD", options_available=False),  # fails require_options
            "EXCLUDED": _snapshot("EXCLUDED"),
        }
    )
    universe_provider = _FakeUniverseProvider(["GOOD", "BAD", "EXCLUDED"])

    result = await run_screen(
        settings, market_data_provider, universe_provider, provider_name="fake"
    )

    assert result.universe_size == 2  # EXCLUDED never reaches the market-data provider
    symbols = [c.symbol for c in result.candidates]
    assert symbols == ["GOOD"]
    assert "BAD" in result.suppressed
    assert any("options" in reason for reason in result.suppressed["BAD"])
    assert result.candidates[0].run_id == result.run_id


async def test_run_screen_sorts_by_score_descending_and_bounds_max_candidates():
    settings = ScreenerSettings(max_candidates=2)
    market_data_provider = _FakeMarketDataProvider(
        {
            "A": _snapshot("A", session_volume=3_000_000.0),  # RVOL 1.5x
            "B": _snapshot("B", session_volume=8_000_000.0),  # RVOL 4x -> highest score
            "C": _snapshot("C", session_volume=4_000_000.0),  # RVOL 2x
        }
    )
    universe_provider = _FakeUniverseProvider(["A", "B", "C"])

    result = await run_screen(
        settings, market_data_provider, universe_provider, provider_name="fake"
    )

    assert len(result.candidates) == 2  # bounded by max_candidates
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)
    assert result.candidates[0].symbol == "B"


async def test_always_include_is_unioned_with_discovered_symbols():
    settings = ScreenerSettings()
    market_data_provider = _FakeMarketDataProvider(
        {"DISCOVERED": _snapshot("DISCOVERED"), "SPY": _snapshot("SPY")}
    )
    universe_provider = _FakeUniverseProvider(["DISCOVERED"])

    result = await run_screen(
        settings,
        market_data_provider,
        universe_provider,
        provider_name="fake",
        always_include=["SPY", "DISCOVERED"],  # duplicate must be deduped
    )

    assert result.universe_size == 2
    assert {c.symbol for c in result.candidates} == {"DISCOVERED", "SPY"}
