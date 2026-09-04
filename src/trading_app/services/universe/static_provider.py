"""Static universe provider — returns `ScreenerSettings.universe`
unchanged. Default; this is the original, fixed-list screener behavior.
"""
from __future__ import annotations

from trading_app.config import Settings


class StaticUniverseProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def discover_symbols(self) -> list[str]:
        return list(self._settings.screener.universe)
