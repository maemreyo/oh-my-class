"""Transactional outbox for durable run-event delivery (#471).

RunEvent rows and their outbox rows are inserted in the same transaction.
Publishing is at-least-once; consumers deduplicate by ``(run_id, sequence)``.
A crash after notification but before ``mark_published`` therefore causes a
safe replay instead of silent event loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select

from services.gateway.teaching_pack_models import RunEventOutbox
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ClaimedRunEvent:
    outbox_id: int
    run_id: RunId
    sequence: int
    dedupe_key: str
    attempts: int


class RunEventOutboxStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, run_id: RunId, sequence: int) -> None:
        self._session.add(RunEventOutbox(
            run_id=run_id,
            sequence=sequence,
            dedupe_key=f"{run_id}:{sequence}",
            status="pending",
            attempts=0,
        ))
        await self._session.flush()

    async def claim_batch(
        self,
        *,
        lease_owner: str,
        limit: int = 100,
        lease_seconds: int = 30,
        now: datetime | None = None,
    ) -> list[ClaimedRunEvent]:
        claim_time = now or datetime.now(UTC)
        statement = (
            select(RunEventOutbox)
            .where(
                or_(
                    RunEventOutbox.status == "pending",
                    and_(
                        RunEventOutbox.status == "publishing",
                        RunEventOutbox.lease_expires_at.is_not(None),
                        RunEventOutbox.lease_expires_at <= claim_time,
                    ),
                ),
                or_(RunEventOutbox.available_at.is_(None), RunEventOutbox.available_at <= claim_time),
            )
            .order_by(RunEventOutbox.run_id, RunEventOutbox.sequence)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        rows = list((await self._session.execute(statement)).scalars().all())
        for row in rows:
            row.status = "publishing"
            row.lease_owner = lease_owner
            row.lease_expires_at = claim_time + timedelta(seconds=lease_seconds)
            row.attempts += 1
        if rows:
            await self._session.flush()
        return [
            ClaimedRunEvent(
                outbox_id=row.outbox_id,
                run_id=RunId(row.run_id),
                sequence=row.sequence,
                dedupe_key=row.dedupe_key,
                attempts=row.attempts,
            )
            for row in rows
        ]

    async def mark_published(self, outbox_id: int, *, now: datetime | None = None) -> bool:
        row = await self._for_update(outbox_id)
        if row is None or row.status != "publishing":
            return False
        row.status = "published"
        row.published_at = now or datetime.now(UTC)
        row.lease_owner = None
        row.lease_expires_at = None
        row.last_error = None
        await self._session.flush()
        return True

    async def mark_retry(
        self,
        outbox_id: int,
        *,
        error_summary: str,
        available_at: datetime,
    ) -> bool:
        row = await self._for_update(outbox_id)
        if row is None or row.status != "publishing":
            return False
        row.status = "pending"
        row.available_at = available_at
        row.lease_owner = None
        row.lease_expires_at = None
        row.last_error = error_summary[:2_000]
        await self._session.flush()
        return True

    async def _for_update(self, outbox_id: int) -> RunEventOutbox | None:
        statement = (
            select(RunEventOutbox)
            .where(RunEventOutbox.outbox_id == outbox_id)
            .with_for_update()
        )
        return (await self._session.execute(statement)).scalar_one_or_none()


async def publish_run_event_outbox(
    session: AsyncSession,
    *,
    worker_id: str,
    limit: int = 100,
) -> int:
    """Publish one ordered batch and persist acknowledgements.

    Notification is intentionally outside a separate broker abstraction: the
    existing ``notify_run_event`` wakes local/SSE subscribers, while the DB
    event ledger remains the replay source of truth.
    """
    from services.gateway.teaching_pack_event_bus import notify_run_event

    store = RunEventOutboxStore(session)
    claimed = await store.claim_batch(lease_owner=worker_id, limit=limit)
    published = 0
    for item in claimed:
        try:
            notify_run_event(item.run_id)
        except Exception as exc:
            delay = min(60, 2 ** min(item.attempts, 6))
            await store.mark_retry(
                item.outbox_id,
                error_summary=str(exc),
                available_at=datetime.now(UTC) + timedelta(seconds=delay),
            )
            continue
        if await store.mark_published(item.outbox_id):
            published += 1
    return published
