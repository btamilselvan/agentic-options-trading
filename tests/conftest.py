from __future__ import annotations

import os
from pathlib import Path

# Tests must never touch whatever DATABASE__URL a developer's real .env
# points at (Supabase/Postgres in normal use) — pin an isolated, throwaway
# SQLite file *before* trading_app.config is imported anywhere, so the very
# first Settings() built in this process already has it.
_TEST_DB_PATH = Path(__file__).parent / ".test_trading_app.db"
os.environ["DATABASE__URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from trading_app.config import get_settings  # noqa: E402
from trading_app.db.base import init_models  # noqa: E402
from trading_app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _fresh_test_database():
    _TEST_DB_PATH.unlink(missing_ok=True)
    yield
    _TEST_DB_PATH.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def client():
    # get_settings() is a process-wide lru_cache singleton, and some
    # endpoints (e.g. the live-mode switch) mutate it in place. Clear the
    # cache so each test starts from fresh, unmutated settings rather than
    # leaking state from whatever test ran before it.
    get_settings.cache_clear()
    # Tests bypass Alembic entirely and create tables directly against the
    # isolated SQLite file above — fast, and independent of whatever
    # migration state a real (Postgres/Supabase) database happens to be in.
    await init_models()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
