"""Teacher-mediated, non-identifiable class recap sharing (TSP-09, ADR-046 amendment).

A recap is a short, templated summary built *only* from TSP-05's
`class_concept_rollup` output -- the same class-level/concept-grouped
aggregate `generate_recommendation_candidates` (recommendations.py) already
treats as the sole evidence source. This module deliberately never imports
`student_drill_down`, `get_session_raw_responses`, or `SessionStudentResponse`:
`MisconceptionRollupRow` has no per-student field to leak in the first place,
so the content-safety boundary is structural, not just a runtime check (see
`test_teaching_session_recap.py::test_module_never_touches_raw_response_table`
for the guard that keeps it that way).

The retention-tier check below is a second, belt-and-suspenders guard: a
pseudonymous/identifiable session's aggregate rows are just as safe to read
as an aggregate-tier session's (the aggregate table never carries a student
field regardless of tier -- see `responses.py`'s `SessionResponseAggregate`),
but TSP-09 asks for this to be a hard boundary rather than "safe today,
fragile tomorrow": richer tiers are refused outright, not merely discouraged.

Flow mirrors `recommendations.py`'s pending/approved shape: `generate_class_
recap` persists a `DRAFT` the teacher can edit (`update_class_recap_draft`)
any number of times, and only `share_class_recap` mints the opaque,
unauthenticated share token and logs the audit event -- reusing TSP-01's
`SessionAuditEvent` (never a new PII-bearing table) exactly as
`approve_recommendation` does for "recommendation_approved". The event stores
a SHA-256 of the shared text, not the text itself, per TSP-09 AC5.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base, utc_now
from services.gateway.teaching_session.models import (
    RetentionTier,
    SessionAuditEvent,
    TeachingSession,
)
from services.gateway.teaching_session.responses import (
    MisconceptionRollupRow,
    class_concept_rollup,
    get_session_aggregates,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Retention-tier guard (hard content-safety boundary, not just policy)
# ---------------------------------------------------------------------------

# Only these tiers may ever produce a recap. `NONE` has nothing to summarize
# (no AGGREGATES category at all -- see retention.py's `_ALLOWED_CATEGORIES`)
# so it degrades to an empty/generic recap rather than an error; richer tiers
# are refused outright, never silently downgraded to "just read the aggregate
# table and hope" -- see module docstring.
_RECAP_ALLOWED_TIERS = frozenset({RetentionTier.NONE, RetentionTier.AGGREGATE})


@dataclass(frozen=True, slots=True)
class RecapRejected:
    reason: str  # "session_not_found" | "retention_tier_too_identifying"


# ---------------------------------------------------------------------------
# Templated recap text (pure, aggregate-only input)
# ---------------------------------------------------------------------------

# ponytail: a flat templated summary, not an LLM call -- TSP-09 doesn't ask
# for generated prose, and a template keeps the aggregate-only guarantee
# trivially checkable (no model call that could "helpfully" invent a detail).
# Upgrade to an LLM rewrite of this same rollup if teachers ask for more
# natural phrasing; the input contract (rollup only) would not change.
_STRONG_ACCURACY_THRESHOLD = 0.8
_WEAK_ACCURACY_THRESHOLD = 0.5


def build_recap_text(rollup: list[MisconceptionRollupRow]) -> str:
    """Build the templated recap from a class-concept rollup -- the only input this takes.

    Never receives a student pseudonym, name, or ID: `MisconceptionRollupRow`
    has no such field, so there is nothing here for one to accidentally leak.
    """
    if not rollup:
        return "Lớp mình chưa có dữ liệu hoạt động nào trong buổi học này."

    total_attempts = sum(row.attempt_count for row in rollup)
    total_correct = sum(row.correct_count for row in rollup)
    accuracy = (total_correct / total_attempts) if total_attempts else 0.0

    strong = [
        row.key for row in rollup
        if row.attempt_count > 0 and (row.correct_count / row.attempt_count) >= _STRONG_ACCURACY_THRESHOLD
    ]
    weak = [
        row.key for row in rollup
        if row.attempt_count > 0 and (row.correct_count / row.attempt_count) < _WEAK_ACCURACY_THRESHOLD
    ]

    lines = [
        f"Lớp mình học được {len(rollup)} nội dung hôm nay, "
        f"với {total_attempts} lượt trả lời và độ chính xác trung bình {accuracy:.0%}.",
    ]
    if strong:
        lines.append("Phần lớp mình làm tốt: " + ", ".join(strong) + ".")
    if weak:
        lines.append("Phần lớp mình cần ôn thêm: " + ", ".join(weak) + ".")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Storage: draft -> shared, mirroring recommendations.py's pending -> approved
# ---------------------------------------------------------------------------


class RecapStatus(StrEnum):
    DRAFT = "draft"
    SHARED = "shared"


class SessionClassRecap(Base):
    """A generated recap awaiting (or holding) teacher review/edit and share.

    `text` is teacher-editable while `status == DRAFT` (`update_class_recap_
    draft`) and frozen once `share_class_recap` moves it to `SHARED`.
    `share_token` is only set on share -- an opaque, unauthenticated lookup
    key (`get_shared_recap`), never a parent login/account.
    """

    __tablename__ = "session_class_recaps"
    __table_args__ = (
        Index("ix_session_class_recaps_session_id", "session_id"),
        Index("ix_session_class_recaps_share_token", "share_token"),
        {"schema": "public"},
    )

    recap_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RecapStatus.DRAFT.value,
    )
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shared_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


async def generate_class_recap(
    db: AsyncSession, *, session_id: str, teacher_id: str,
) -> SessionClassRecap | RecapRejected:
    """Teacher-triggered recap draft (TSP-09 AC1/AC2).

    Reads only `TeachingSession.retention_tier` (to gate) and the aggregate
    rollup below -- never the raw per-student response table, regardless of
    what tier the session actually has. Returns `RecapRejected` for a
    pseudonymous/identifiable session instead of degrading silently.
    """
    session = await db.get(TeachingSession, session_id)
    if session is None:
        return RecapRejected(reason="session_not_found")
    if session.retention_tier not in _RECAP_ALLOWED_TIERS:
        return RecapRejected(reason="retention_tier_too_identifying")

    aggregates = await get_session_aggregates(db, session_id=session_id)
    rollup = class_concept_rollup(aggregates)
    text = build_recap_text(rollup)

    recap = SessionClassRecap(
        recap_id=f"recap-{uuid4()}",
        session_id=session_id,
        text=text,
        created_by=teacher_id,
    )
    db.add(recap)
    await db.flush()
    return recap


async def update_class_recap_draft(
    db: AsyncSession, *, recap_id: str, text: str,
) -> SessionClassRecap:
    """Teacher edits the draft text before sharing (TSP-09 AC2).

    Raises `OMCError` (NOT_FOUND/VALIDATION_ERROR) if the recap doesn't exist
    or is already shared -- shared text is frozen, matching `recommendations.
    approve_recommendation`'s "not pending" guard.
    """
    recap = await db.get(SessionClassRecap, recap_id)
    if recap is None:
        raise OMCError(error_code=ErrorCode.NOT_FOUND, message=f"Recap {recap_id!r} not found")
    if recap.status != RecapStatus.DRAFT.value:
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Recap {recap_id!r} is already shared and cannot be edited",
            details=[{"field": "status", "reason": "recap_not_draft"}],
        )
    recap.text = text
    await db.flush()
    return recap


async def share_class_recap(
    db: AsyncSession, *, recap_id: str, teacher_id: str,
) -> SessionClassRecap:
    """Teacher-confirmed share (TSP-09 AC2/AC3): mints the opaque share token.

    Logs one `SessionAuditEvent` (action="class_recap_shared") carrying the
    SHA-256 of the shared text, never the text itself -- the audit trail
    proves *that* a recap was shared and by whom, without becoming a second
    copy of the shared content (TSP-09 AC5).
    """
    recap = await db.get(SessionClassRecap, recap_id)
    if recap is None:
        raise OMCError(error_code=ErrorCode.NOT_FOUND, message=f"Recap {recap_id!r} not found")
    if recap.status == RecapStatus.SHARED.value:
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Recap {recap_id!r} was already shared",
            details=[{"field": "status", "reason": "recap_already_shared"}],
        )

    recap.status = RecapStatus.SHARED.value
    recap.share_token = secrets.token_urlsafe(24)
    recap.shared_at = utc_now()
    recap.shared_by = teacher_id

    db.add(SessionAuditEvent(
        event_id=f"audit-{uuid4()}",
        session_id=recap.session_id,
        actor_id=teacher_id,
        action="class_recap_shared",
        event_metadata={
            "recap_id": recap_id,
            "text_sha256": hashlib.sha256(recap.text.encode("utf-8")).hexdigest(),
            "char_count": len(recap.text),
        },
    ))
    await db.flush()
    return recap


async def get_shared_recap(db: AsyncSession, *, share_token: str) -> SessionClassRecap | None:
    """Public, unauthenticated lookup by opaque token -- no parent login/account.

    Only ever returns an already-`SHARED` recap; a draft has no `share_token`
    to be looked up by in the first place.
    """
    result = await db.execute(
        select(SessionClassRecap).where(SessionClassRecap.share_token == share_token),
    )
    return result.scalar_one_or_none()
