"""Background loop that computes feature snapshots for the current
screener candidates on a configurable cadence during market hours
(requirements.md section 4.2). Runs under `WorkerManager` (see
`workers/manager.py`) — never in a request handler.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from trading_app.config import get_settings
from trading_app.db.base import get_session_factory
from trading_app.db.repositories.features import save_feature_snapshot
from trading_app.db.repositories.screener import get_latest_candidates
from trading_app.services.market_data.factory import get_market_data_provider
from trading_app.services.quant.service import compute_snapshots_for_candidates
from trading_app.services.screener.market_hours import is_regular_market_session

logger = logging.getLogger(__name__)


async def run_quant_loop() -> None:
    while True:
        settings = get_settings()
        cfg = settings.quant_engine
        if cfg.market_hours_only and not is_regular_market_session():
            logger.debug("quant engine: outside regular market hours, skipping this cycle")
        else:
            try:
                async with get_session_factory()() as session:
                    candidate_records = await get_latest_candidates(session)
                candidates = [
                    (record.symbol, UUID(record.correlation_id)) for record in candidate_records
                ]
                if candidates:
                    provider = get_market_data_provider(settings)
                    snapshots = await compute_snapshots_for_candidates(candidates, provider, cfg)
                    async with get_session_factory()() as session:
                        for snapshot in snapshots:
                            await save_feature_snapshot(session, snapshot)
                    logger.info("quant engine: persisted %d feature snapshots", len(snapshots))
                else:
                    logger.debug(
                        "quant engine: no current screener candidates, nothing to compute"
                    )
            except Exception:
                logger.exception("quant engine run failed")
        await asyncio.sleep(cfg.refresh_interval_seconds)
