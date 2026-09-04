"""Verifies symbol extraction against a real, captured
`/marketdata/v1/movers/{index}` response (requirements.md section 1:
verified field mapping, not assumed)."""
from __future__ import annotations

from trading_app.services.universe.schwab_movers_provider import symbols_from_movers_response

# Captured live from a real, authenticated Schwab Trader API call
# (EQUITY_ALL sorted by VOLUME).
_REAL_MOVERS_RESPONSE = {
    "screeners": [
        {
            "description": "SUNPOWER INC",
            "volume": 292831509,
            "lastPrice": 0.35,
            "netChange": 0.09,
            "marketShare": 1.86,
            "totalVolume": 15773402037,
            "trades": 357757,
            "netPercentChange": 0.3695,
            "symbol": "SPWR",
        },
        {
            "description": "GOPRO INC A",
            "volume": 179025133,
            "lastPrice": 1.45,
            "netChange": -0.24,
            "marketShare": 1.13,
            "totalVolume": 15773402037,
            "trades": 268407,
            "netPercentChange": -0.142,
            "symbol": "GPRO",
        },
        {
            "description": "NVIDIA CORP",
            "volume": 134681610,
            "lastPrice": 229.62,
            "netChange": 5.21,
            "marketShare": 0.85,
            "totalVolume": 15773402037,
            "trades": 1448639,
            "netPercentChange": 0.0232,
            "symbol": "NVDA",
        },
    ]
}


def test_extracts_symbols_from_real_response():
    symbols = symbols_from_movers_response(_REAL_MOVERS_RESPONSE)
    assert symbols == ["SPWR", "GPRO", "NVDA"]


def test_empty_screeners_list_yields_no_symbols():
    assert symbols_from_movers_response({"screeners": []}) == []


def test_missing_screeners_key_yields_no_symbols():
    assert symbols_from_movers_response({}) == []
