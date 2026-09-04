"""snapshot_from_quote_entry against a real, captured
`/marketdata/v1/quotes?fields=quote,fundamental,reference` response
(requirements.md section 1: verified field mapping, not assumed)."""
from __future__ import annotations

from datetime import timedelta

from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.schwab_client import snapshot_from_quote_entry

# Captured live from a real, authenticated Schwab Trader API call.
_AAPL_ENTRY = {
    "assetMainType": "EQUITY",
    "assetSubType": "COE",
    "quoteType": "NBBO",
    "realtime": True,
    "ssid": 1973757747,
    "symbol": "AAPL",
    "fundamental": {
        "avg10DaysVolume": 39838826.0,
        "avg1YearVolume": 52435140.0,
        "eps": 7.46,
        "peRatio": 37.27858,
        "sharesOutstanding": 14594180000,
    },
    "quote": {
        "askPrice": 327.84,
        "askSize": 520,
        "bidPrice": 327.6,
        "bidSize": 80,
        "closePrice": 324.96,
        "highPrice": 330.81,
        "lastPrice": 327.7,
        "lowPrice": 324.11,
        "netChange": 2.74,
        "netPercentChange": 0.8431807,
        "openPrice": 324.87,
        "quoteTime": 1788479999053,
        "securityStatus": "Closed",
        "totalVolume": 37225838,
        "tradeTime": 1788479998053,
    },
    "reference": {
        "cusip": "037833100",
        "description": "APPLE INC",
        "exchange": "Q",
        "exchangeName": "Nasdaq",
        "isHardToBorrow": False,
        "isShortable": True,
        "optionable": True,
    },
}


def test_maps_real_response_fields():
    snapshot = snapshot_from_quote_entry("AAPL", _AAPL_ENTRY, timedelta(days=365 * 10))

    assert snapshot.symbol == "AAPL"
    assert snapshot.last_price == 327.7
    assert snapshot.prior_close == 324.96
    assert snapshot.session_volume == 37225838
    assert snapshot.avg_volume_baseline == 39838826.0
    assert snapshot.bid == 327.6
    assert snapshot.ask == 327.84
    assert snapshot.options_available is True
    assert snapshot.source == "schwab"
    assert snapshot.market_timestamp.isoformat() == "2026-09-03T23:59:59.053000+00:00"


def test_recent_quote_is_fresh():
    from trading_app.schemas.common import utcnow

    entry = {
        **_AAPL_ENTRY,
        "quote": {
            **_AAPL_ENTRY["quote"],
            "quoteTime": int((utcnow() - timedelta(minutes=1)).timestamp() * 1000),
        },
    }
    snapshot = snapshot_from_quote_entry("AAPL", entry, timedelta(seconds=900))
    assert snapshot.freshness == DataFreshness.FRESH


def test_old_quote_is_stale():
    from trading_app.schemas.common import utcnow

    entry = {
        **_AAPL_ENTRY,
        "quote": {
            **_AAPL_ENTRY["quote"],
            "quoteTime": int((utcnow() - timedelta(hours=2)).timestamp() * 1000),
        },
    }
    snapshot = snapshot_from_quote_entry("AAPL", entry, timedelta(seconds=900))
    assert snapshot.freshness == DataFreshness.STALE


def test_missing_fundamental_and_reference_default_gracefully():
    entry = {"quote": _AAPL_ENTRY["quote"]}
    snapshot = snapshot_from_quote_entry("AAPL", entry, timedelta(days=1))
    assert snapshot.avg_volume_baseline is None
    assert snapshot.options_available is False
