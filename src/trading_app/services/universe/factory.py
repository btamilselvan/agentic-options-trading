"""Provider selection for universe discovery — mirrors
`services/market_data/factory.py`'s pattern. `UNIVERSE__PROVIDER` is the
only switch; add a provider by implementing `UniverseProvider` and
registering it here.
"""
from __future__ import annotations

from collections.abc import Callable

from trading_app.config import Settings
from trading_app.services.universe.base import UniverseProvider
from trading_app.services.universe.schwab_movers_provider import SchwabMoversUniverseProvider
from trading_app.services.universe.static_provider import StaticUniverseProvider

_PROVIDERS: dict[str, Callable[[Settings], UniverseProvider]] = {
    "static": StaticUniverseProvider,
    "schwab_movers": SchwabMoversUniverseProvider,
}


def get_universe_provider(settings: Settings) -> UniverseProvider:
    try:
        factory = _PROVIDERS[settings.universe.provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown UNIVERSE__PROVIDER={settings.universe.provider!r}; "
            f"expected one of {sorted(_PROVIDERS)}."
        ) from exc
    return factory(settings)
