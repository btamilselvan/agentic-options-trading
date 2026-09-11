"""Background worker lifecycle.

Request handlers must never block on market-data loops, LLM calls, or
broker reconciliation (requirements.md section 9). This manager starts each
background loop as an asyncio task under the FastAPI lifespan and cancels
them cleanly on shutdown. `screener` and `indicators` run real logic
(requirements.md sections 4.1, 4.2); the rest are placeholders until their
owning component (Phase 1-4) is implemented. Swap in a durable task queue
(per requirements.md sections 7, 9) before relying on this for real
scheduling guarantees.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from trading_app.workers.quant_worker import run_quant_loop
from trading_app.workers.screener_worker import run_screener_loop

logger = logging.getLogger(__name__)

# Named in requirements.md section 9, minus "screener"/"indicators" (real
# logic — see above) plus "screener" itself (section 4.1's own
# configurable refresh cadence, which needs a loop just as much as these).
PLACEHOLDER_WORKER_NAMES = (
    "collection",
    "event_detection",
    "llm_evaluation",
    "paper_fills",
    "reconciliation",
    "notifications",
)


async def _placeholder_loop(name: str, interval_seconds: float = 60.0) -> None:
    while True:
        logger.debug("worker %s tick", name)
        await asyncio.sleep(interval_seconds)


def _make_placeholder(name: str) -> Callable[[], Coroutine[Any, Any, None]]:
    async def _loop() -> None:
        await _placeholder_loop(name)

    return _loop


def _build_worker_loops() -> dict[str, Callable[[], Coroutine[Any, Any, None]]]:
    loops: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {
        "screener": run_screener_loop,
        "indicators": run_quant_loop,
    }
    for name in PLACEHOLDER_WORKER_NAMES:
        loops[name] = _make_placeholder(name)
    return loops


class WorkerManager:
    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []

    def start(self) -> None:
        for name, loop_factory in _build_worker_loops().items():
            task = asyncio.create_task(loop_factory(), name=f"worker:{name}")
            self._tasks.append(task)
        logger.info("started %d background workers", len(self._tasks))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("stopped background workers")
