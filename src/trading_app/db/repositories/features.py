"""Persistence for computed feature snapshots (requirements.md section
4.2)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.models.features import FeatureSnapshotRecord
from trading_app.schemas.features import FeatureSnapshot


async def save_feature_snapshot(session: AsyncSession, snapshot: FeatureSnapshot) -> None:
    session.add(
        FeatureSnapshotRecord(
            symbol=snapshot.symbol,
            as_of=snapshot.as_of,
            feature_definition_version=snapshot.feature_definition_version,
            features=snapshot.features,
            market_context=snapshot.market_context,
            data_quality=snapshot.data_quality.value,
            correlation_id=str(snapshot.correlation_id),
        )
    )
    await session.commit()


async def get_snapshot_history(
    session: AsyncSession, symbol: str, limit: int = 50
) -> list[FeatureSnapshotRecord]:
    stmt = (
        select(FeatureSnapshotRecord)
        .where(FeatureSnapshotRecord.symbol == symbol)
        .order_by(FeatureSnapshotRecord.as_of.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_latest_snapshot(session: AsyncSession, symbol: str) -> FeatureSnapshotRecord | None:
    records = await get_snapshot_history(session, symbol, limit=1)
    return records[0] if records else None


async def get_latest_snapshots_for_symbols(
    session: AsyncSession, symbols: list[str] | None = None
) -> list[FeatureSnapshotRecord]:
    """The most recent snapshot per symbol. When `symbols` is None,
    covers every symbol that has ever had a snapshot persisted."""
    stmt = select(FeatureSnapshotRecord).order_by(
        FeatureSnapshotRecord.symbol, FeatureSnapshotRecord.as_of.desc()
    )
    if symbols is not None:
        stmt = stmt.where(FeatureSnapshotRecord.symbol.in_(symbols))
    all_records = (await session.execute(stmt)).scalars().all()

    latest_by_symbol: dict[str, FeatureSnapshotRecord] = {}
    for record in all_records:
        if record.symbol not in latest_by_symbol:
            latest_by_symbol[record.symbol] = record
    return list(latest_by_symbol.values())
