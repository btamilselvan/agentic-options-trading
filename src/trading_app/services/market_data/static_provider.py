"""Deterministic placeholder market-data source.

Used until a validated, broker-backed provider (Schwab, once its
market-data entitlement/coverage/rate limits/timestamp semantics are
verified per requirements.md section 1) is wired in behind the same
`MarketDataProvider` interface. Output is NOT real market data — it's a
reproducible synthetic snapshot/bar series seeded from each symbol's
name, so the screener/quant engine (and their tests) have something
deterministic to run against without any network access or credentials.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from trading_app.schemas.common import utcnow
from trading_app.schemas.market_data import Candle, DataFreshness, Interval
from trading_app.services.market_data.base import MarketSnapshot

_SOURCE_NAME = "static-dev-fixture"

_MARKET_TZ = ZoneInfo("America/New_York")
_PREMARKET_OPEN = time(4, 0)
_SESSION_OPEN = time(9, 30)
_SESSION_CLOSE = time(16, 0)
_INTERVAL_MINUTES = {Interval.ONE_MIN: 1, Interval.FIVE_MIN: 5, Interval.FIFTEEN_MIN: 15}


def _seeded_random(key: str) -> random.Random:
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _trading_days(n: int, *, include_today: bool) -> list[date]:
    """The `n` most recent weekdays, oldest first. `include_today=False`
    for daily bars — today's daily bar isn't closed until session end,
    and evaluating an incomplete bar as closed is exactly what
    requirements.md section 8 says to avoid."""
    days: list[date] = []
    cursor = datetime.now(tz=_MARKET_TZ).date()
    if not include_today:
        cursor -= timedelta(days=1)
    while len(days) < n:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


class StaticMarketDataProvider:
    async def get_market_snapshots(self, symbols: list[str]) -> list[MarketSnapshot]:
        return [self._synthesize_snapshot(symbol) for symbol in symbols]

    async def get_candles(
        self,
        symbol: str,
        interval: Interval,
        *,
        lookback_days: int,
        include_extended_hours: bool = False,
    ) -> list[Candle]:
        rng = _seeded_random(f"{symbol}:{interval.value}:{lookback_days}")
        price = round(rng.uniform(10.0, 500.0), 2)

        if interval == Interval.DAILY:
            return self._synthesize_daily(symbol, rng, price, lookback_days)
        return self._synthesize_intraday(
            symbol, interval, rng, price, lookback_days, include_extended_hours
        )

    def _synthesize_snapshot(self, symbol: str) -> MarketSnapshot:
        rng = _seeded_random(symbol)
        prior_close = round(rng.uniform(10.0, 500.0), 2)
        last_price = round(prior_close * (1 + rng.uniform(-0.05, 0.05)), 2)
        avg_volume_baseline = rng.uniform(1_000_000, 20_000_000)
        session_volume = avg_volume_baseline * rng.uniform(0.3, 3.0)
        spread = last_price * rng.uniform(0.0005, 0.01)
        bid = round(last_price - spread / 2, 2)
        ask = round(last_price + spread / 2, 2)
        return MarketSnapshot(
            symbol=symbol,
            last_price=last_price,
            prior_close=prior_close,
            session_volume=session_volume,
            avg_volume_baseline=avg_volume_baseline,
            bid=bid,
            ask=ask,
            options_available=rng.random() > 0.1,
            market_timestamp=utcnow(),
            source=_SOURCE_NAME,
            freshness=DataFreshness.FRESH,
        )

    def _synthesize_daily(
        self, symbol: str, rng: random.Random, price: float, lookback_days: int
    ) -> list[Candle]:
        candles: list[Candle] = []
        for day in _trading_days(lookback_days, include_today=False):
            open_price = price
            close_price = round(open_price * (1 + rng.uniform(-0.03, 0.03)), 2)
            high = round(max(open_price, close_price) * (1 + rng.uniform(0, 0.01)), 2)
            low = round(min(open_price, close_price) * (1 - rng.uniform(0, 0.01)), 2)
            volume = rng.uniform(1_000_000, 20_000_000)
            candles.append(
                Candle(
                    symbol=symbol,
                    interval=Interval.DAILY,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close_price,
                    volume=volume,
                    market_timestamp=datetime.combine(day, _SESSION_CLOSE, tzinfo=_MARKET_TZ),
                    source=_SOURCE_NAME,
                    freshness=DataFreshness.FRESH,
                )
            )
            price = close_price
        return candles

    def _synthesize_intraday(
        self,
        symbol: str,
        interval: Interval,
        rng: random.Random,
        price: float,
        lookback_days: int,
        include_extended_hours: bool,
    ) -> list[Candle]:
        step = timedelta(minutes=_INTERVAL_MINUTES[interval])
        now = datetime.now(tz=_MARKET_TZ)
        today = now.date()
        candles: list[Candle] = []

        for day in _trading_days(lookback_days, include_today=True):
            session_start_time = _PREMARKET_OPEN if include_extended_hours else _SESSION_OPEN
            cursor = datetime.combine(day, session_start_time, tzinfo=_MARKET_TZ)
            session_end = datetime.combine(day, _SESSION_CLOSE, tzinfo=_MARKET_TZ)
            while cursor + step <= session_end and (day != today or cursor + step <= now):
                open_price = price
                close_price = round(open_price * (1 + rng.uniform(-0.002, 0.002)), 2)
                high = round(max(open_price, close_price) * (1 + rng.uniform(0, 0.0015)), 2)
                low = round(min(open_price, close_price) * (1 - rng.uniform(0, 0.0015)), 2)
                volume = rng.uniform(500, 50_000)
                candles.append(
                    Candle(
                        symbol=symbol,
                        interval=interval,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close_price,
                        volume=volume,
                        market_timestamp=cursor,
                        source=_SOURCE_NAME,
                        freshness=DataFreshness.FRESH,
                    )
                )
                price = close_price
                cursor += step
        return candles
