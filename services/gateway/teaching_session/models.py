"""SQLAlchemy models and enums for the TeachingSession lifecycle (TSP-01).

A TeachingSession is a privacy-first overlay on top of an immutable slide-deck
snapshot (ADR-046 decisions 1-2): it carries lifecycle state and retention
policy, but it never mutates the deck it points to. `deck_id` and
`snapshot_id` are kept as opaque strings on purpose -- SDTF-01 (stable slide/
block/interaction IDs) and SDTF-06 (immutable snapshot storage) are being
designed/implemented separately and may formalize those references further;
this module does not block on or couple to their exact shape.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from services.gateway.models import Base, utc_now


class SessionStatus(StrEnum):
    """TeachingSession lifecycle states (ADR-046 decision 1 / TSP-01 AC1)."""

    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class DeliveryMode(StrEnum):
    """How a session's deck snapshot is delivered (TSP-07 AC1/amendment).

    Declared for all five modes now so adding the async ones later is not a
    breaking schema change -- but only ``LIVE`` has a working runtime in this
    slice (TSP-07 amendment: v1 implements live only). See
    `teaching_session.delivery_mode` for each mode's declared response/
    retention/sync policy, and `teaching_session.service.create_session` for
    the fail-closed gate that rejects any non-live mode today.
    """

    LIVE = "live"
    HOMEWORK = "homework"
    REVIEW = "review"
    FLIPPED = "flipped"
    CATCH_UP = "catch_up"


class RetentionTier(StrEnum):
    """Student-response retention levels (ADR-046 decision 5 / TSP-01 AC3).

    Ordered least to most identifying. ``AGGREGATE`` is the K-12-safe default
    (TSP-01 AC4) -- never ``IDENTIFIABLE`` by default.
    """

    NONE = "none"
    AGGREGATE = "aggregate"
    PSEUDONYMOUS = "pseudonymous"
    IDENTIFIABLE = "identifiable"


class SessionDataCategory(StrEnum):
    """Distinct categories of data a session can produce (TSP-01 AC6).

    Kept as a conceptual/type-level distinction in this slice rather than
    separate tables -- each category has its own retention and
    identity-exposure story, expressed in `teaching_session/retention.py`'s
    `allowed_data_categories_for_tier`.
    """

    EVENTS = "events"
    AGGREGATES = "aggregates"
    RAW_RESPONSES = "raw_responses"
    TEACHER_REFLECTIONS = "teacher_reflections"
    AI_SUGGESTIONS = "ai_suggestions"
    EXPORTS = "exports"


class TeachingSession(Base):
    """A scheduled/live/ended classroom delivery of an immutable deck snapshot.

    Binds to `deck_id` + `snapshot_id` (+ future stable slide/block/
    interaction IDs) without mutating the underlying deck (ADR-046 decision
    2). Retention tier is chosen once at creation -- see
    `teaching_session.retention.validate_retention_selection` for the
    class_id/acknowledgment rules enforced before a row is ever constructed,
    and `_lock_retention_tier` below for the structural guard against a later
    silent escalation (TSP-01 amendment #3).
    """

    __tablename__ = "teaching_sessions"
    __table_args__ = (
        Index("ix_teaching_sessions_teacher_id", "teacher_id"),
        Index("ix_teaching_sessions_class_id", "class_id"),
        Index("ix_teaching_sessions_deck_id", "deck_id"),
        Index("ix_teaching_sessions_room_code", "room_code"),
        {"schema": "public"},
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # The anonymous-first join affordance (TSP-02): QR-primary, this 6-digit
    # code is the camera-less fallback. No DB-level uniqueness constraint --
    # `teaching_session.join.find_joinable_session_by_room_code` already
    # scopes lookups to non-terminal sessions, so an ended session's old code
    # can be safely reused; see `service._unique_room_code`'s ponytail note.
    room_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    # None => anonymous open-join room (ADR-046 decision 3). A real,
    # non-empty class_id is required to select pseudonymous/identifiable
    # retention (TSP-01 amendment #4). NOTE: `users` has no `organization_id`
    # column yet (tracked separately in
    # .scratch/multi-tenancy/organization-id-migration.md), so "org-scoped"
    # is approximated today as "bound to a real class_id" -- the same
    # fail-closed approximation `services/gateway/auth/ownership.py` uses for
    # cross-tenant checks. Tighten this once that migration lands.
    class_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deck_id: Mapped[str] = mapped_column(String(80), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False),
        nullable=False,
        default=SessionStatus.SCHEDULED,
    )
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        Enum(DeliveryMode, native_enum=False),
        nullable=False,
        default=DeliveryMode.LIVE,
    )
    retention_tier: Mapped[RetentionTier] = mapped_column(
        Enum(RetentionTier, native_enum=False),
        nullable=False,
        default=RetentionTier.AGGREGATE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @validates("retention_tier")
    def _lock_retention_tier(self, _key: str, value: RetentionTier) -> RetentionTier:
        """Retention tier is chosen once and cannot silently escalate mid-session.

        (TSP-01 amendment #3 / ADR-046 decision 26.) SQLAlchemy calls
        `@validates` hooks on every assignment, including the constructor's
        first `self.retention_tier = ...` -- at that point `self.__dict__`
        has no `retention_tier` entry yet, so the first assignment always
        succeeds. Any later reassignment to a *different* value raises;
        reassigning the same value (e.g. re-loading from the DB) is a no-op.
        """
        current = self.__dict__.get("retention_tier")
        if current is not None and current != value:
            msg = (
                f"retention_tier is locked at session creation "
                f"(was {current!r}, attempted {value!r})"
            )
            raise ValueError(msg)
        return value


class SessionAuditEvent(Base):
    """Persisted, session-scoped audit trail.

    TSP-01's own minimal seed of PRIV-01's eventual data-access audit log
    (ADR-046 amendment #25 / TSP-01 amendment #2): built now, shaped so a
    future PRIV-01 data-access log can absorb it rather than replace it.
    Never stores student data or session content -- only who/what/when of an
    access or consent decision (e.g. the identifiable-tier acknowledgment
    required by TSP-01 amendment #3).
    """

    __tablename__ = "teaching_session_audit_events"
    __table_args__ = (
        Index("ix_teaching_session_audit_events_session_id", "session_id"),
        {"schema": "public"},
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.teaching_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClassRosterEntry(Base):
    """A roster row (name + optional student ID) scoped to a `class_id` (TSP-02 amendment #4).

    Populated only via CSV import (`teaching_session.roster.import_roster`) so
    `identifiable`-tier sessions can offer a name-select dropdown at join
    instead of free-text entry. No relation to `users` -- a roster entry never
    creates or implies a login-capable account, and there is no external SIS
    integration in this slice.
    """

    __tablename__ = "class_roster_entries"
    __table_args__ = (
        Index("ix_class_roster_entries_class_id", "class_id"),
        {"schema": "public"},
    )

    roster_entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    class_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imported_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TeachingSessionEvent(Base):
    """Append-only significant-event log (TSP-03 base AC1/amendment).

    Postgres is the write-behind source of truth behind the Redis-hot
    `SessionReadModel` (`teaching_session.events.SessionReadModel`) -- see
    `teaching_session/event_log.py::record_event`. `sequence` is a
    per-session monotonic counter (mirrors `RunEvent.sequence` in
    `teaching_pack_models.py`), not a global id, so "resume after event N"
    (base AC5) is scoped per session. `idempotency_key` is nullable and only
    set by student-submission routes (base AC6) -- Postgres treats NULLs as
    distinct for the unique constraint, so non-idempotent event types (slide
    changes, etc.) are unaffected.
    """

    __tablename__ = "teaching_session_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "sequence", name="uq_teaching_session_events_session_sequence",
        ),
        UniqueConstraint(
            "session_id", "idempotency_key", name="uq_teaching_session_events_idempotency_key",
        ),
        Index("ix_teaching_session_events_session_id_sequence", "session_id", "sequence"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.teaching_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
