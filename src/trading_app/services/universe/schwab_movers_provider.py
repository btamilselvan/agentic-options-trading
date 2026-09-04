"""Dynamic universe discovery via Schwab's Movers endpoint
(requirements.md section 4.1) — real top gainers/losers/most-active
symbols instead of a fixed list. Response schema (`{"screeners": [...]}`)
verified against a real, authenticated call, not assumed (requirements.md
section 1) — see `tests/test_schwab_movers.py`.

`GET /marketdata/v1/movers/{index}` returns only the top 10 for one
index/sort-order combination, so this combines every configured
`(index, sort_order)` pair and dedupes, to cover more of the market than
a single call would.
"""
from __future__ import annotations

import logging
from pathlib import Path

from schwab.auth import client_from_token_file
from schwab.client import Client

from trading_app.config import Settings
from trading_app.services.market_data.base import MarketDataProviderError
from trading_app.services.universe.base import UniverseProviderError

logger = logging.getLogger(__name__)

_INDEX_MAP = {
    "dji": Client.Movers.Index.DJI,
    "compx": Client.Movers.Index.COMPX,
    "spx": Client.Movers.Index.SPX,
    "nyse": Client.Movers.Index.NYSE,
    "nasdaq": Client.Movers.Index.NASDAQ,
    "otcbb": Client.Movers.Index.OTCBB,
    "index_all": Client.Movers.Index.INDEX_ALL,
    "equity_all": Client.Movers.Index.EQUITY_ALL,
    "option_all": Client.Movers.Index.OPTION_ALL,
    "option_put": Client.Movers.Index.OPTION_PUT,
    "option_call": Client.Movers.Index.OPTION_CALL,
}
_SORT_ORDER_MAP = {
    "volume": Client.Movers.SortOrder.VOLUME,
    "trades": Client.Movers.SortOrder.TRADES,
    "percent_change_up": Client.Movers.SortOrder.PERCENT_CHANGE_UP,
    "percent_change_down": Client.Movers.SortOrder.PERCENT_CHANGE_DOWN,
}


class SchwabMoversUniverseProvider:
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
        self._client = client_from_token_file(
            token_path=settings.schwab_token_path,
            api_key=settings.schwab_client_id,
            app_secret=settings.schwab_client_secret,
            asyncio=True,
        )
        self._indices = [_INDEX_MAP[name] for name in settings.universe.schwab_movers_indices]
        self._sort_orders = [
            _SORT_ORDER_MAP[name] for name in settings.universe.schwab_movers_sort_orders
        ]
        self._max_symbols = settings.universe.max_dynamic_symbols

    async def discover_symbols(self) -> list[str]:
        symbols: list[str] = []
        seen: set[str] = set()

        for index in self._indices:
            for sort_order in self._sort_orders:
                response = await self._client.get_movers(index, sort_order=sort_order)
                if response.status_code != 200:
                    logger.warning(
                        "Schwab movers call failed for %s/%s: HTTP %s",
                        index,
                        sort_order,
                        response.status_code,
                    )
                    continue
                for symbol in symbols_from_movers_response(response.json()):
                    if symbol not in seen:
                        seen.add(symbol)
                        symbols.append(symbol)

        if not symbols:
            raise UniverseProviderError(
                "Schwab movers discovery returned no symbols across all "
                "configured index/sort-order combinations."
            )
        return symbols[: self._max_symbols]


def symbols_from_movers_response(payload: dict) -> list[str]:
    """Pure extraction from one `/marketdata/v1/movers/{index}` response —
    standalone so it's testable against a captured real response without
    live credentials."""
    return [entry["symbol"] for entry in payload.get("screeners", []) if entry.get("symbol")]
