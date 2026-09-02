"""FastAPI application factory and entrypoint.

Request handlers must never block on market-data loops, LLM calls, or
broker reconciliation (requirements.md section 9) — that work runs in the
durable background workers started here under the app's lifespan, not in
request handlers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from trading_app.api.routers import api_router
from trading_app.config import get_settings
from trading_app.correlation import CorrelationIdMiddleware
from trading_app.logging_config import configure_logging
from trading_app.workers.manager import WorkerManager

configure_logging()

worker_manager = WorkerManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is Alembic-managed (see migrations/), not created by the app
    # at runtime — run `alembic upgrade head` before starting this process
    # (the Docker entrypoint does this automatically).
    worker_manager.start()
    try:
        yield
    finally:
        await worker_manager.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Personal intraday agentic options-trading decision-support "
            "application. See requirements.md for the full specification. "
            "The LLM is advisory only and cannot place, modify, or cancel "
            "an order."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    """Entrypoint for the `trading-app` console script."""
    import uvicorn

    uvicorn.run("trading_app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
