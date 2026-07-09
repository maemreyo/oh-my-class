"""Postgres append-only event store + recovery (TSP-03).

`append_event`/`_next_sequence` mirror `teaching_pack_store.py`'s
`RunEvent`/`_next_sequence` shape (advisory-lock-guarded per-session
monotonic sequence) -- same pattern, independent implementation, since a
TeachingSession event is not a TeachingPack run event. Idempotency handling
(`on_conflict_do_nothing` + a follow-up lookup) mirrors
`teaching_pack_job_store.py`'s idempotency-key upsert.

`record_event` is the one function callers use: it appends to Postgres (the
source of truth -- this either succeeds or raises normally, e.g. on a
db-level constraint violation) and returns the new derived `SessionReadModel`
computed from Redis-hot state if available, else `recover_read_model`'s
Postgres replay. It does **not** touch Redis for writing -- callers (see
`routers/teaching_session_live.py`) call `db.commit()` first, then
`live_sync.set_hot_state`/`publish_event` after, so a Redis subscriber never
observes an event that a failed commit later rolled back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.teaching_session import live_sync
from services.gateway.teaching_session.events import (
    SessionEvent,
    SessionEventType,
    SessionReadModel,
    apply_event,
    build_event,
    initial_read_model,
)
from services.gateway.teaching_session.models import TeachingSessionEvent
from services.gateway.teaching_session.tokens import SessionRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ponytail: replay the last N events, not the full history, per the
# amendment's literal recovery mechanism. Safe because `apply_event` is
# last-write-wins per field (see events.py docstring), so missing very old
# events only matters if the session's current slide/tally state was set
# further back than N events ago -- 500 comfortably covers a single class
# period's worth of slide changes + student submissions. Raise this (or move
# to a Postgres-side materialized snapshot) if a session ever legitimately
# runs longer than that between hot-state refreshes.
DEFAULT_RECOVERY_EVENT_LIMIT = 500


@dataclass(frozen=True, slots=True)
class RecordedEvent:
    row: TeachingSessionEvent
    event: SessionEvent
    duplicate: bool
    read_model: SessionReadModel


async def lock_session_events(db: AsyncSession, session_id: str) -> None:
    """Serialize concurrent event writes for one session within this transaction.

    Postgres advisory xact locks are transaction-scoped (released at
    commit/rollback) and re-entrant within the same session/transaction, so
    a caller that needs to check-then-act on an idempotency key (e.g.
    `routers/teaching_session_live.py::submit_response`, which calls
    TSP-05's `responses.record_response` in between the check and the
    event-log write) can take this lock *before* the check to close the
    race window, and `append_event` below can safely take it again.
    """
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": session_id})


async def find_by_idempotency_key(
    db: AsyncSession, session_id: str, idempotency_key: str,
) -> TeachingSessionEvent | None:
    result = await db.execute(
        select(TeachingSessionEvent).where(
            TeachingSessionEvent.session_id == session_id,
            TeachingSessionEvent.idempotency_key == idempotency_key,
        ),
    )
    return result.scalar_one_or_none()


async def append_event(
    db: AsyncSession,
    *,
    session_id: str,
    event_type: SessionEventType,
    actor_role: SessionRole,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> tuple[TeachingSessionEvent, bool]:
    """Insert one event, assigning the next per-session sequence.

    Returns `(row, created)`. `created=False` means `idempotency_key` already
    existed for this session -- `row` is the *original* recorded event, and
    the caller must not re-apply side effects (base AC6: duplicate
    submissions are rejected, not double-counted).
    """
    await lock_session_events(db, session_id)
    sequence = await _next_sequence(db, session_id)
    event = build_event(
        session_id=session_id, event_type=event_type, actor_role=actor_role, payload=payload,
    )

    insert_statement = pg_insert(TeachingSessionEvent).values(
        event_id=event.event_id,
        session_id=session_id,
        sequence=sequence,
        event_type=event_type.value,
        actor_role=actor_role.value,
        payload=event.payload,
        idempotency_key=idempotency_key,
        created_at=event.created_at,
    )
    if idempotency_key is not None:
        insert_statement = insert_statement.on_conflict_do_nothing(
            index_elements=["session_id", "idempotency_key"],
        )
    result = await db.execute(insert_statement.returning(TeachingSessionEvent.id))
    inserted_id = result.scalar_one_or_none()
    await db.flush()

    if inserted_id is None and idempotency_key is not None:
        existing = await find_by_idempotency_key(db, session_id, idempotency_key)
        assert existing is not None  # the conflict we just hit is exactly this row
        return existing, False

    row = await db.get(TeachingSessionEvent, inserted_id)
    assert row is not None  # just inserted in this same transaction
    return row, True


async def _next_sequence(db: AsyncSession, session_id: str) -> int:
    statement = select(func.coalesce(func.max(TeachingSessionEvent.sequence), 0) + 1).where(
        TeachingSessionEvent.session_id == session_id,
    )
    result = await db.execute(statement)
    return result.scalar_one()


async def replay_events(
    db: AsyncSession,
    session_id: str,
    *,
    after_sequence: int = 0,
    limit: int | None = None,
) -> list[TeachingSessionEvent]:
    """All events after `after_sequence`, in order -- base AC5 "resume via last event ID"."""
    statement = (
        select(TeachingSessionEvent)
        .where(
            TeachingSessionEvent.session_id == session_id,
            TeachingSessionEvent.sequence > after_sequence,
        )
        .order_by(TeachingSessionEvent.sequence)
    )
    if limit is not None:
        statement = statement.limit(limit)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def recover_read_model(
    db: AsyncSession,
    session_id: str,
    *,
    limit: int = DEFAULT_RECOVERY_EVENT_LIMIT,
) -> SessionReadModel:
    """Rebuild the derived state from the last `limit` Postgres events (TSP-03 amendment:
    "on Redis restart/failover, reconstruct state by replaying the last N Postgres events")."""
    statement = (
        select(TeachingSessionEvent)
        .where(TeachingSessionEvent.session_id == session_id)
        .order_by(TeachingSessionEvent.sequence.desc())
        .limit(limit)
    )
    result = await db.execute(statement)
    rows = list(reversed(result.scalars().all()))
    state = initial_read_model(session_id)
    for row in rows:
        state = apply_event(state, row_to_event(row))
    return state


def row_to_event(row: TeachingSessionEvent) -> SessionEvent:
    return SessionEvent(
        event_id=row.event_id,
        session_id=row.session_id,
        event_type=SessionEventType(row.event_type),
        actor_role=SessionRole(row.actor_role),
        payload=row.payload,
        created_at=row.created_at,
        sequence=row.sequence,
    )


async def current_state(db: AsyncSession, session_id: str) -> SessionReadModel:
    """Redis-hot state, falling back to Postgres replay recovery on a miss/outage."""
    return await live_sync.get_hot_state(session_id) or await recover_read_model(db, session_id)


async def record_event(
    db: AsyncSession,
    *,
    session_id: str,
    event_type: SessionEventType,
    actor_role: SessionRole,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> RecordedEvent:
    """Append the event to Postgres and compute the resulting derived state.

    Does not commit and does not touch Redis -- see module docstring for why
    that's the caller's job, in that order.
    """
    row, created = await append_event(
        db,
        session_id=session_id,
        event_type=event_type,
        actor_role=actor_role,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    event = row_to_event(row)
    if not created:
        state = await current_state(db, session_id)
        return RecordedEvent(row=row, event=event, duplicate=True, read_model=state)

    previous_state = await current_state(db, session_id)
    next_state = apply_event(previous_state, event)
    return RecordedEvent(row=row, event=event, duplicate=False, read_model=next_state)
