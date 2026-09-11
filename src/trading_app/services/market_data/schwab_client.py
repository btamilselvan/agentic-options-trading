"""Schwab-backed MarketDataProvider (requirements.md sections 1, 4.2).

The field mappings below are verified against real, authenticated
responses — not assumed from documentation alone, per requirements.md
section 1's "validation required" policy:
- `GET /marketdata/v1/quotes?fields=quote,fundamental,reference` —
  `reference.optionable` gives options availability directly; no
  separate option-chain call needed.
- `GET /marketdata/v1/pricehistory` (via schwab-py's
  `get_price_history_every_{minute,five_minutes,fifteen_minutes,day}`)
  — `{"symbol", "empty", "candles": [{"open","high","low","close",
  "volume","datetime"}]}`, `datetime` in epoch milliseconds. No default
  date range is applied server-side, so `get_candles` always passes an
  explicit `start_datetime`/`end_datetime`.

This module never performs the interactive OAuth consent flow itself —
`scripts/bootstrap_schwab_oauth.py` does that once, and
`scripts/refresh_schwab_token.py` can force a refresh without a browser.
This module only ever reads the token file those scripts maintain and
lets schwab-py's async session refresh the access token silently as
needed on each call.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from schwab.auth import client_from_token_file
from schwab.client import Client

from trading_app.config import Settings
from trading_app.schemas.common import utcnow
from trading_app.schemas.market_data import Candle, DataFreshness, Interval
from trading_app.services.market_data.base import MarketDataProviderError, MarketSnapshot

logger = logging.getLogger(__name__)

_MARKET_TZ = ZoneInfo("America/New_York")
_SOURCE_NAME = "schwab"
_QUOTE_FIELDS = [
    Client.Quote.Fields.QUOTE,
    Client.Quote.Fields.FUNDAMENTAL,
    Client.Quote.Fields.REFERENCE,
]
_PRICE_HISTORY_METHODS = {
    Interval.ONE_MIN: "get_price_history_every_minute",
    Interval.FIVE_MIN: "get_price_history_every_five_minutes",
    Interval.FIFTEEN_MIN: "get_price_history_every_fifteen_minutes",
    Interval.DAILY: "get_price_history_every_day",
}


class SchwabMarketDataProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.schwab_client_id or not settings.schwab_client_secret:
            raise MarketDataProviderError(
                "SCHWAB_CLIENT_ID/SCHWAB_CLIENT_SECRET are not configured — "
                "register an app at https://developer.schwab.com and set "
                "them in .env."
            )
        if not Path(settings.schwab_token_path).exists():
            raise MarketDataProviderError(
                f"No Schwab OAuth token at {settings.schwab_token_path} — run "
                "`uv run scripts/bootstrap_schwab_oauth.py` first."
            )
        # asyncio=True: get_quotes() must be awaited and never blocks the
        # event loop (requirements.md section 9) — the sync client schwab-py
        # otherwise returns is fine for the one-off scripts/ but wrong here.
        self._client = client_from_token_file(
            token_path=settings.schwab_token_path,
            api_key=settings.schwab_client_id,
            app_secret=settings.schwab_client_secret,
            asyncio=True,
        )
        self._max_quote_age = timedelta(seconds=settings.market_data.max_quote_age_seconds)

    async def get_market_snapshots(self, symbols: list[str]) -> list[MarketSnapshot]:
        if not symbols:
            return []
        response = await self._client.get_quotes(symbols, fields=_QUOTE_FIELDS)
        if response.status_code != 200:
            raise MarketDataProviderError(
                f"Schwab quotes call failed: HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )
        payload = response.json()

        snapshots = []
        for symbol in symbols:
            entry = payload.get(symbol)
            if entry is None or "quote" not in entry:
                logger.warning("Schwab quotes response missing data for %s", symbol)
                continue
            snapshots.append(snapshot_from_quote_entry(symbol, entry, self._max_quote_age))
        return snapshots

    async def get_candles(
        self,
        symbol: str,
        interval: Interval,
        *,
        lookback_days: int,
        include_extended_hours: bool = False,
    ) -> list[Candle]:
        method = getattr(self._client, _PRICE_HISTORY_METHODS[interval])
        end_datetime = datetime.now(tz=UTC)
        # Generous calendar-day buffer (weekends/holidays) around the
        # requested trading-day lookback; Schwab simply has no data for
        # non-trading days, so over-requesting here is harmless.
        start_datetime = end_datetime - timedelta(days=lookback_days * 2 + 5)
        response = await method(
            symbol,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            need_extended_hours_data=include_extended_hours,
            need_previous_close=True,
        )
        if response.status_code != 200:
            raise MarketDataProviderError(
                f"Schwab price history call failed for {symbol}/{interval.value}: "
                f"HTTP {response.status_code}: {response.text[:300]}"
            )
        body = response.json()
        candles = [
            candle_from_price_history_entry(symbol, interval, entry)
            for entry in body.get("candles", [])
        ]
        candles.sort(key=lambda c: c.market_timestamp)
        if interval == Interval.DAILY:
            # Schwab's daily-bar endpoint includes today's bar even while
            # the session is still open, with a "close" that's actually
            # just today's live price, not a closed value — exactly the
            # incomplete-bar-as-closed-bar case requirements.md section 8
            # warns against, and something callers (levels.py's "previous
            # day" convention) explicitly rely on not happening.
            today = datetime.now(tz=_MARKET_TZ).date()
            candles = [
                c for c in candles if c.market_timestamp.astimezone(_MARKET_TZ).date() != today
            ]
        return candles


def candle_from_price_history_entry(symbol: str, interval: Interval, entry: dict) -> Candle:
    """Pure mapping from one `/marketdata/v1/pricehistory` candle entry
    to our provider-neutral Candle — standalone so it's testable against
    a captured real response without live credentials."""
    datetime_ms = entry.get("datetime")
    market_timestamp = (
        datetime.fromtimestamp(datetime_ms / 1000, tz=UTC) if datetime_ms else utcnow()
    )
    return Candle(
        symbol=symbol,
        interval=interval,
        open=entry.get("open"),
        high=entry.get("high"),
        low=entry.get("low"),
        close=entry.get("close"),
        volume=entry.get("volume"),
        market_timestamp=market_timestamp,
        source=_SOURCE_NAME,
        freshness=DataFreshness.FRESH,
    )


def snapshot_from_quote_entry(
    symbol: str, entry: dict, max_quote_age: timedelta
) -> MarketSnapshot:
    """Pure mapping from one symbol's entry in a `/marketdata/v1/quotes`
    response to our provider-neutral MarketSnapshot — standalone so it's
    testable against a captured real response without live credentials."""
    quote = entry.get("quote", {})
    fundamental = entry.get("fundamental", {})
    reference = entry.get("reference", {})

    quote_time_ms = quote.get("quoteTime")
    market_timestamp = (
        datetime.fromtimestamp(quote_time_ms / 1000, tz=UTC) if quote_time_ms else utcnow()
    )
    freshness = (
        DataFreshness.FRESH
        if utcnow() - market_timestamp <= max_quote_age
        else DataFreshness.STALE
    )

    return MarketSnapshot(
        symbol=symbol,
        last_price=quote.get("lastPrice"),
        prior_close=quote.get("closePrice"),
        session_volume=quote.get("totalVolume"),
        avg_volume_baseline=fundamental.get("avg10DaysVolume"),
        bid=quote.get("bidPrice"),
        ask=quote.get("askPrice"),
        options_available=bool(reference.get("optionable", False)),
        market_timestamp=market_timestamp,
        source=_SOURCE_NAME,
        freshness=freshness,
    )
