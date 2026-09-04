"""Regular-session gate for the screener's refresh cadence (requirements.md
sections 4.1, 8).

This checks only the regular Mon-Fri 09:30-16:00 America/New_York window.
It does NOT yet account for market holidays, early closes, or other
exchange-calendar exceptions (requirements.md section 8) — that needs a
real exchange-calendar source and is a deliberate later refinement, not an
oversight.
"""
from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

_MARKET_TZ = ZoneInfo("America/New_York")
_SESSION_OPEN = time(9, 30)
_SESSION_CLOSE = time(16, 0)


def is_regular_market_session(now: datetime | None = None) -> bool:
    moment = (now or datetime.now(tz=UTC)).astimezone(_MARKET_TZ)
    if moment.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return _SESSION_OPEN <= moment.time() < _SESSION_CLOSE
