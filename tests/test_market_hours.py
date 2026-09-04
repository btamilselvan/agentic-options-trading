from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from trading_app.services.screener.market_hours import is_regular_market_session

_ET = ZoneInfo("America/New_York")


def test_monday_mid_session_is_open():
    monday_10am = datetime(2026, 9, 7, 10, 0, tzinfo=_ET)
    assert is_regular_market_session(monday_10am) is True


def test_monday_before_open_is_closed():
    monday_8am = datetime(2026, 9, 7, 8, 0, tzinfo=_ET)
    assert is_regular_market_session(monday_8am) is False


def test_monday_after_close_is_closed():
    monday_5pm = datetime(2026, 9, 7, 17, 0, tzinfo=_ET)
    assert is_regular_market_session(monday_5pm) is False


def test_saturday_is_closed():
    saturday_noon = datetime(2026, 9, 12, 12, 0, tzinfo=_ET)
    assert is_regular_market_session(saturday_noon) is False


def test_utc_input_is_converted_to_market_timezone():
    # 14:00 UTC on a September weekday is 10:00 America/New_York (EDT, UTC-4).
    moment = datetime(2026, 9, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
    assert is_regular_market_session(moment) is True
