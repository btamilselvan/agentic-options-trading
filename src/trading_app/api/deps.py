"""Shared FastAPI dependencies."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.db.base import get_db_session


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session
