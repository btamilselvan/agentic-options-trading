"""End-to-end: trigger a screening run, then a feature computation, then
read snapshots back through the API — proves the engine, persistence,
and routing are wired together correctly (requirements.md section 4.2)."""
from __future__ import annotations

from trading_app.config import QuantEngineSettings
from trading_app.services.market_data.static_provider import StaticMarketDataProvider
from trading_app.services.quant.service import compute_snapshots_for_candidates


async def test_compute_snapshots_for_no_candidates_returns_empty():
    # Isolated unit-level check (no shared test DB/app involved) — the
    # client fixture shares one DB across the whole test session, so a
    # true "nothing persisted yet" API-level scenario isn't reliably
    # constructible here once other tests have already run.
    snapshots = await compute_snapshots_for_candidates(
        [], StaticMarketDataProvider(), QuantEngineSettings()
    )
    assert snapshots == []


async def test_trigger_screen_then_compute_then_list_snapshots(client):
    screen_response = await client.post("/api/v1/candidates/run")
    assert screen_response.status_code == 200
    run = screen_response.json()

    compute_response = await client.post("/api/v1/features/compute")
    assert compute_response.status_code == 200
    snapshots = compute_response.json()
    assert len(snapshots) == run["candidate_count"]

    if not snapshots:
        return  # nothing further to assert when the screen found no candidates

    for snapshot in snapshots:
        assert snapshot["feature_definition_version"]
        assert "vwap" in snapshot["features"]
        assert "ema_9" in snapshot["features"]
        assert "spy_trend" in snapshot["market_context"]

    all_response = await client.get("/api/v1/features/snapshots")
    assert all_response.status_code == 200
    all_snapshots = all_response.json()
    assert {s["symbol"] for s in snapshots} <= {s["symbol"] for s in all_snapshots}

    symbol = snapshots[0]["symbol"]
    scoped_response = await client.get(f"/api/v1/features/snapshots?symbol={symbol}")
    assert scoped_response.status_code == 200
    scoped = scoped_response.json()
    assert len(scoped) >= 1
    assert all(s["symbol"] == symbol for s in scoped)
