"""Provider selection for market data — mirrors
`services/insights/factory.py`'s pattern. `MARKET_DATA__PROVIDER` is the
only switch; add a provider by implementing `MarketDataProvider` and
registering it here.
"""
from __future__ import annotations

from collections.abc import Callable

from trading_app.config import Settings
from trading_app.services.market_data.base import MarketDataProvider
from trading_app.services.market_data.schwab_client import SchwabMarketDataProvider
from trading_app.services.market_data.static_provider import StaticMarketDataProvider

_PROVIDERS: dict[str, Callable[[Settings], MarketDataProvider]] = {
    "static": lambda settings: StaticMarketDataProvider(),
    "schwab": SchwabMarketDataProvider,
}


def get_market_data_provider(settings: Settings) -> MarketDataProvider:
    try:
        factory = _PROVIDERS[settings.market_data.provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown MARKET_DATA__PROVIDER={settings.market_data.provider!r}; "
            f"expected one of {sorted(_PROVIDERS)}."
        ) from exc
    return factory(settings)
