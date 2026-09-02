from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from trading_app.config import get_settings
from trading_app.main import create_app


@pytest_asyncio.fixture
async def client():
    # get_settings() is a process-wide lru_cache singleton, and some
    # endpoints (e.g. the live-mode switch) mutate it in place. Clear the
    # cache so each test starts from fresh, unmutated settings rather than
    # leaking state from whatever test ran before it.
    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
