"""Background loop that refreshes the screener's candidate watchlist on a
configurable cadence during market hours (requirements.md section 4.1).
Runs under `WorkerManager` (see `workers/manager.py`) — never in a
request handler.
"""
from __future__ import annotations

import asyncio
import logging

from trading_app.config import get_settings
from trading_app.db.base import get_session_factory
from trading_app.db.repositories.screener import save_screen_result
from trading_app.services.market_data.factory import get_market_data_provider
from trading_app.services.screener.market_hours import is_regular_market_session
from trading_app.services.screener.service import run_screen
from trading_app.services.universe.factory import get_universe_provider

logger = logging.getLogger(__name__)


async def run_screener_loop() -> None:
    while True:
        settings = get_settings()
        cfg = settings.screener
        if cfg.market_hours_only and not is_regular_market_session():
            logger.debug("screener: outside regular market hours, skipping this cycle")
        else:
            try:
                market_data_provider = get_market_data_provider(settings)
                universe_provider = get_universe_provider(settings)
                result = await run_screen(
                    cfg,
                    market_data_provider,
                    universe_provider,
                    provider_name=settings.market_data.provider,
                    always_include=settings.universe.always_include,
                )
                async with get_session_factory()() as session:
                    await save_screen_result(session, result)
                logger.info(
                    "screener run %s: %d/%d candidates persisted",
                    result.run_id,
                    len(result.candidates),
                    result.universe_size,
                )
            except Exception:
                logger.exception("screener run failed")
        await asyncio.sleep(cfg.refresh_interval_seconds)
