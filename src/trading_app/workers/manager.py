"""Background worker lifecycle.

Request handlers must never block on market-data loops, LLM calls, or
broker reconciliation (requirements.md section 9). This manager starts each
background loop as an asyncio task under the FastAPI lifespan and cancels
them cleanly on shutdown. Each loop body is a placeholder until its owning
component (Phase 1-4) is implemented; swap in a durable task queue (per
requirements.md sections 7, 9) before relying on this for real scheduling
guarantees.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

WORKER_NAMES = (
    "collection",
    "indicators",
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


class WorkerManager:
    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        for name in WORKER_NAMES:
            task = asyncio.create_task(_placeholder_loop(name), name=f"worker:{name}")
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
