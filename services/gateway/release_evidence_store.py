"""Release evidence store — persistence layer for evidence records.

Provides insert, query-by-run-id, and list operations on the
``release_evidence`` table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from services.gateway.release_evidence import (
    ReleaseEvidence,
    ReleaseEvidenceRecord,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_evidence(evidence: ReleaseEvidence, db: AsyncSession) -> None:
    """Persist an evidence record (upsert on run_id)."""
    record = evidence.to_db_record()
    await db.merge(record)
    await db.flush()


async def get_evidence(run_id: str, db: AsyncSession) -> ReleaseEvidence | None:
    """Fetch evidence by run_id.  Returns None if not found."""
    statement = select(ReleaseEvidenceRecord).where(
        ReleaseEvidenceRecord.run_id == run_id,
    )
    result = await db.execute(statement)
    record = result.scalar_one_or_none()
    if record is None:
        return None
    return ReleaseEvidence.from_db_record(record)


async def list_evidence(
    db: AsyncSession,
    *,
    limit: int = 50,
) -> list[ReleaseEvidence]:
    """List recent evidence records, newest first."""
    statement = (
        select(ReleaseEvidenceRecord)
        .order_by(ReleaseEvidenceRecord.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(statement)
    records = result.scalars().all()
    return [ReleaseEvidence.from_db_record(r) for r in records]
