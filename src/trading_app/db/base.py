"""Async SQLAlchemy engine/session setup.

Real schema evolution is owned by Alembic (see migrations/) — `init_models`
below is `Base.metadata.create_all`, kept only as a fast, migration-free
way to stand up a throwaway schema for tests. The application itself never
calls it; run `alembic upgrade head` before starting the app.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from trading_app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database.url, echo=settings.database.echo)
        if _engine.dialect.name == "sqlite":
            # SQLite doesn't enforce foreign keys by default — without this,
            # bugs that violate a FK constraint (e.g. inserting a child row
            # before its parent) pass silently here and only surface against
            # a real Postgres database. Make local/test runs behave the
            # same way in this respect.
            @event.listens_for(_engine.sync_engine, "connect")
            def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_models() -> None:
    """Create tables if they do not exist. Test-only convenience — see the
    module docstring."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
