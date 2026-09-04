"""Screener entry point (requirements.md section 4.1): discover a
universe, fetch raw market data for it, apply deterministic filters, rank
survivors, and bound the result to a watchlist — persistence is a
separate step (see `trading_app.db.repositories.screener`) so this stays
independently testable without a database.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from trading_app.config import ScreenerSettings
from trading_app.schemas.candidates import CandidateSymbol
from trading_app.schemas.common import utcnow
from trading_app.services.market_data.base import MarketDataProvider
from trading_app.services.screener.filters import evaluate_filters
from trading_app.services.screener.metrics import compute_metrics
from trading_app.services.screener.scoring import score_symbol
from trading_app.services.universe.base import UniverseProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScreenResult:
    run_id: str
    started_at: datetime
    completed_at: datetime
    universe_size: int
    market_data_provider: str
    candidates: list[CandidateSymbol]
    # symbol -> failure reasons, kept for observability (requirements.md
    # section 4.3's "record suppressed events and the reason" principle
    # applies just as much to the screener's own filtering).
    suppressed: dict[str, list[str]] = field(default_factory=dict)


async def run_screen(
    settings: ScreenerSettings,
    market_data_provider: MarketDataProvider,
    universe_provider: UniverseProvider,
    *,
    provider_name: str,
    always_include: list[str] | None = None,
) -> ScreenResult:
    run_id = str(uuid4())
    started_at = utcnow()

    discovered = await universe_provider.discover_symbols()
    combined = [*(always_include or []), *discovered]
    exclusions = set(settings.exclusions)
    # dict.fromkeys dedupes while preserving discovery order.
    universe = [symbol for symbol in dict.fromkeys(combined) if symbol not in exclusions]
    snapshots = await market_data_provider.get_market_snapshots(universe)

    candidates: list[CandidateSymbol] = []
    suppressed: dict[str, list[str]] = {}

    for snapshot in snapshots:
        metrics = compute_metrics(snapshot)
        logger.debug(
            "screener run %s: symbol %s: metrics=%s",
            run_id,
            snapshot.symbol,
            metrics
        )
        failures = evaluate_filters(snapshot, metrics, settings)
        if failures:
            suppressed[snapshot.symbol] = failures
            logger.debug(
                "screener run %s: symbol %s: suppressed, reasons=%s",
                run_id,
                snapshot.symbol,
                failures,
            )
            continue
        score, reasons = score_symbol(metrics, snapshot, settings)
        candidates.append(
            CandidateSymbol(
                symbol=snapshot.symbol,
                score=score,
                reasons=reasons,
                as_of=snapshot.market_timestamp,
                source_freshness=snapshot.freshness,
                run_id=run_id,
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    bounded = candidates[: settings.max_candidates]
    if len(candidates) > len(bounded):
        logger.info(
            "screener run %s: dropped %d candidates beyond max_candidates=%d",
            run_id,
            len(candidates) - len(bounded),
            settings.max_candidates,
        )

    return ScreenResult(
        run_id=run_id,
        started_at=started_at,
        completed_at=utcnow(),
        universe_size=len(universe),
        market_data_provider=provider_name,
        candidates=bounded,
        suppressed=suppressed,
    )
