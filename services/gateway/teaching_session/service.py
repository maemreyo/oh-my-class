"""Creation-time glue for TeachingSession (TSP-01).

Validates the retention tier selection, then persists the session and (for
the identifiable tier) its audit acknowledgment in the same unit of work.
Callers are expected to `await db.commit()`; this module only adds and
flushes, matching the store convention used elsewhere in this gateway (see
`services/gateway/outcome_store.py`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.teaching_session.delivery_mode import IMPLEMENTED_DELIVERY_MODES
from services.gateway.teaching_session.join import JOINABLE_STATUSES, generate_room_code
from services.gateway.teaching_session.models import (
    DeliveryMode,
    RetentionTier,
    SessionAuditEvent,
    TeachingSession,
)
from services.gateway.teaching_session.retention import (
    RetentionSelectionRejected,
    validate_retention_selection,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_MAX_ROOM_CODE_ATTEMPTS = 5


async def create_session(
    db: AsyncSession,
    *,
    session_id: str,
    teacher_id: str,
    deck_id: str,
    snapshot_id: str,
    class_id: str | None = None,
    retention_tier: RetentionTier = RetentionTier.AGGREGATE,
    identifiable_acknowledged: bool = False,
    delivery_mode: DeliveryMode = DeliveryMode.LIVE,
) -> TeachingSession:
    """Create a new TeachingSession, enforcing TSP-01's retention rules.

    Raises:
        OMCError: with `ErrorCode.VALIDATION_ERROR` if the retention tier
            selection is invalid for this session (an identity-bearing tier
            without a real `class_id`, or `identifiable` without an explicit
            acknowledgment), or if `delivery_mode` is anything other than
            `live` (TSP-07 amendment: only live has a working runtime in this
            slice -- the other four modes are declared in the schema/policy
            table for a future slice, not selectable today).
    """
    if delivery_mode not in IMPLEMENTED_DELIVERY_MODES:
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"delivery_mode {delivery_mode.value!r} is not yet supported",
            details=[{"field": "delivery_mode", "reason": "delivery_mode_not_yet_supported"}],
        )

    result = validate_retention_selection(
        tier=retention_tier,
        class_id=class_id,
        identifiable_acknowledged=identifiable_acknowledged,
    )
    if isinstance(result, RetentionSelectionRejected):
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Retention tier {result.tier.value!r} rejected: {result.reason}",
            details=[{"field": "retention_tier", "reason": result.reason}],
        )

    session = TeachingSession(
        session_id=session_id,
        teacher_id=teacher_id,
        class_id=class_id,
        deck_id=deck_id,
        snapshot_id=snapshot_id,
        retention_tier=retention_tier,
        delivery_mode=delivery_mode,
        room_code=await _unique_room_code(db),
    )
    db.add(session)
    # Flush the session row before the audit event: there is no ORM
    # `relationship()` between the two (deliberately -- this stays a plain FK,
    # not a navigable association), so SQLAlchemy's unit-of-work cannot infer
    # insert order on its own and may emit the audit-event INSERT first,
    # violating its FK. Two flushes in one transaction, not two commits.
    await db.flush()

    if retention_tier is RetentionTier.IDENTIFIABLE:
        db.add(SessionAuditEvent(
            event_id=f"audit-{uuid4()}",
            session_id=session_id,
            actor_id=teacher_id,
            action="retention_tier_identifiable_acknowledged",
            event_metadata={"tier": retention_tier.value},
        ))
        await db.flush()

    return session


async def _unique_room_code(db: AsyncSession) -> str:
    """Generate a room code that doesn't collide with another currently-
    joinable session's code.

    ponytail: no DB-level uniqueness constraint on `room_code` -- a terminal
    session's old code is fair game for reuse (`JOINABLE_STATUSES` already
    scopes both this check and `join.find_joinable_session_by_room_code` to
    non-terminal sessions), so a plain retry loop is enough at K-12 traffic
    volume. Upgrade to a partial-unique index if collision retries ever show
    up in prod metrics.
    """
    for _ in range(_MAX_ROOM_CODE_ATTEMPTS):
        candidate = generate_room_code()
        result = await db.execute(
            select(TeachingSession.session_id).where(
                TeachingSession.room_code == candidate,
                TeachingSession.status.in_(JOINABLE_STATUSES),
            ),
        )
        if result.scalar_one_or_none() is None:
            return candidate
    msg = f"Could not generate a unique room code after {_MAX_ROOM_CODE_ATTEMPTS} attempts"
    raise RuntimeError(msg)
