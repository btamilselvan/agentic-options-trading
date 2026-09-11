"""candle_from_price_history_entry against a real, captured
`/marketdata/v1/pricehistory` response (requirements.md section 1:
verified field mapping, not assumed)."""
from __future__ import annotations

from datetime import UTC, datetime

from trading_app.schemas.market_data import Interval
from trading_app.services.market_data.schwab_client import candle_from_price_history_entry

# Captured live from a real, authenticated Schwab Trader API call
# (AAPL, get_price_history_every_day).
_REAL_DAILY_ENTRY = {
    "open": 317.1,
    "high": 320.7,
    "low": 315.27,
    "close": 315.92,
    "volume": 15266928,
    "datetime": 1788840000000,
}


def test_maps_real_daily_entry():
    candle = candle_from_price_history_entry("AAPL", Interval.DAILY, _REAL_DAILY_ENTRY)

    assert candle.symbol == "AAPL"
    assert candle.interval == Interval.DAILY
    assert candle.open == 317.1
    assert candle.high == 320.7
    assert candle.low == 315.27
    assert candle.close == 315.92
    assert candle.volume == 15266928
    assert candle.source == "schwab"
    assert candle.market_timestamp == datetime.fromtimestamp(1788840000000 / 1000, tz=UTC)


def test_missing_datetime_falls_back_to_now_not_a_crash():
    entry = {**_REAL_DAILY_ENTRY, "datetime": None}
    candle = candle_from_price_history_entry("AAPL", Interval.DAILY, entry)
    assert candle.market_timestamp is not None


def test_missing_ohlcv_fields_become_none_not_zero():
    candle = candle_from_price_history_entry("AAPL", Interval.ONE_MIN, {"datetime": 1788840000000})
    assert candle.open is None
    assert candle.volume is None
