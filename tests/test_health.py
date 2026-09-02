from __future__ import annotations


async def test_liveness(client):
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_safety_status_defaults_to_paper_and_live_disabled(client):
    response = await client.get("/api/v1/health/status")
    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "PAPER"
    assert body["live_trading_enabled"] is False
