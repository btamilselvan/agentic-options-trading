"""Alembic environment.

The database URL and target metadata are sourced from the application's
own Settings/Base rather than duplicated here, so `alembic upgrade head`
always operates against the same database the app itself would connect
to (Supabase/Postgres in dev and production, SQLite only as a fallback).
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from trading_app.config import get_settings
from trading_app.db.base import Base

# Import every ORM model module so it registers on Base.metadata before
# autogenerate compares against it. Add new model modules here as they're
# created.
from trading_app.models import audit, screener  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# All application tables — including Alembic's own version table — use
# the "ot_" prefix (see CLAUDE.md) so this database can be shared safely
# with other projects.
VERSION_TABLE = "ot_alembic_version"


def get_url() -> str:
    return get_settings().database.url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    connectable: AsyncEngine = create_async_engine(get_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
