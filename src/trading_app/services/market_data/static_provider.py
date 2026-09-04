"""Deterministic placeholder market-data source.

Used until a validated, broker-backed provider (Schwab, once its
market-data entitlement/coverage/rate limits/timestamp semantics are
verified per requirements.md section 1) is wired in behind the same
`MarketDataProvider` interface. Output is NOT real market data — it's a
reproducible synthetic snapshot seeded from each symbol's name, so the
screener (and its tests) have something deterministic to run against
without any network access or credentials.
"""
from __future__ import annotations

import hashlib
import random

from trading_app.schemas.common import utcnow
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.base import MarketSnapshot

_SOURCE_NAME = "static-dev-fixture"


def _seeded_random(symbol: str) -> random.Random:
    seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


class StaticMarketDataProvider:
    async def get_market_snapshots(self, symbols: list[str]) -> list[MarketSnapshot]:
        return [self._synthesize(symbol) for symbol in symbols]

    def _synthesize(self, symbol: str) -> MarketSnapshot:
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
