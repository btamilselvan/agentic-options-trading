from __future__ import annotations


async def test_live_mode_change_rejects_wrong_confirmation_phrase(client):
    response = await client.post(
        "/api/v1/configuration/safety/live-mode",
        json={
            "enable": True,
            "confirmation_phrase": "wrong",
            "target_broker_account_alias": "robinhood-main",
        },
    )
    assert response.status_code == 400


async def test_live_mode_change_accepts_correct_confirmation_phrase(client):
    response = await client.post(
        "/api/v1/configuration/safety/live-mode",
        json={
            "enable": True,
            "confirmation_phrase": "I understand the risk of live trading",
            "target_broker_account_alias": "robinhood-main",
        },
    )
    assert response.status_code == 200
    assert response.json()["live_trading_enabled"] is True
