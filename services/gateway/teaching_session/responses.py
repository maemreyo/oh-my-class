"""Student response collection and analytics governance (TSP-05, ADR-046).

Structured-first response kinds (base AC1): a multiple-choice selection, a
poll vote, or a short structured value are the default shape and need no
gating -- there is nothing free-text-shaped for PII/safety to screen. Free
text is the one gated variant (base AC2): it is only accepted when the
owning interaction explicitly allows it, the session's own policy allows it,
and it passes `packages.quality.layer2_content.pii.detect_pii` clean.

Retention gating fails closed through `teaching_session.retention.
allowed_data_categories_for_tier` (TSP-01 AC3/4/6): a tier without
`RAW_RESPONSES` (none/aggregate) never gets a raw per-student row -- only the
`SessionResponseAggregate` counter increments. That aggregate table is what
`class_concept_rollup` reads by default (base AC4); `student_drill_down`
requires the raw table and is refused outright below pseudonymous (base AC5).

Every raw response is tagged with `kc_ids: list[str]` in the exact shape
`effectiveness-loop/el-001` already uses on `StudentAttemptRecord`
(`services/gateway/outcome_models.py`) -- this raw capture is designed to
become that subsystem's real input once it is made real, not a second,
parallel analytics layer (amendment #2). No analytics/insights dashboard is
built on top of this module in v1 -- only the rollup and gated drill-down
above, and the non-competitive gamification helpers at the bottom
(amendment #1), whose preference is read from the existing per-teacher
`BaseStore` memory (`packages.agents.teaching_pack.teacher_memory`,
priority-upgrades/002) rather than a new preference table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from packages.quality.layer2_content.pii import detect_pii
from services.gateway.models import Base, utc_now
from services.gateway.teaching_session.models import RetentionTier, SessionDataCategory
from services.gateway.teaching_session.retention import allowed_data_categories_for_tier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Response kinds (base AC1)
# ---------------------------------------------------------------------------


class ResponseKind(StrEnum):
    """Student response shapes -- structured-first.

    MULTIPLE_CHOICE/POLL_VOTE/SHORT_STRUCTURED select or submit a value from
    a bounded set; FREE_TEXT is the only kind `gate_free_text` ever screens.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    POLL_VOTE = "poll_vote"
    SHORT_STRUCTURED = "short_structured"
    FREE_TEXT = "free_text"


STRUCTURED_RESPONSE_KINDS: frozenset[ResponseKind] = frozenset({
    ResponseKind.MULTIPLE_CHOICE, ResponseKind.POLL_VOTE, ResponseKind.SHORT_STRUCTURED,
})


def _validate_payload(kind: ResponseKind, payload: dict[str, Any]) -> str | None:
    """Structural check for a response kind's payload shape. `None` means valid."""
    if kind is ResponseKind.MULTIPLE_CHOICE:
        selected = payload.get("selected_option_ids")
        if not isinstance(selected, list) or not selected:
            return "multiple_choice_requires_selected_option_ids"
        if not all(isinstance(o, str) and o for o in selected):
            return "multiple_choice_requires_selected_option_ids"
    elif kind is ResponseKind.POLL_VOTE:
        selected_id = payload.get("selected_option_id")
        if not isinstance(selected_id, str) or not selected_id:
            return "poll_vote_requires_selected_option_id"
    elif kind is ResponseKind.SHORT_STRUCTURED:
        value = payload.get("value")
        if not isinstance(value, str) or not value or len(value) > 200:
            return "short_structured_requires_bounded_value"
    elif kind is ResponseKind.FREE_TEXT:
        text = payload.get("text")
        if not isinstance(text, str) or not text:
            return "free_text_requires_text"
    return None


# ---------------------------------------------------------------------------
# Free-text gating (base AC2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreeTextAccepted:
    pass


@dataclass(frozen=True, slots=True)
class FreeTextRejected:
    reason: str
    # "interaction_does_not_allow_free_text" | "session_policy_blocks_free_text" | "pii_detected"


type FreeTextGateResult = FreeTextAccepted | FreeTextRejected


def gate_free_text(
    text: str,
    *,
    interaction_allows_free_text: bool,
    session_allows_free_text: bool,
) -> FreeTextGateResult:
    """Base AC2: free text is gated by interaction type, session policy, and PII/safety filtering.

    Fail-closed on *any* `detect_pii` hit, including its low-confidence
    person-name matches -- this is student-authored free text in a K-12
    classroom, a stricter bar than the high-confidence-only check
    `packages.agents.middleware.safety.guardrail` uses for agent output.
    """
    if not interaction_allows_free_text:
        return FreeTextRejected(reason="interaction_does_not_allow_free_text")
    if not session_allows_free_text:
        return FreeTextRejected(reason="session_policy_blocks_free_text")
    audit = detect_pii(text)
    if any(audit.redaction_counts.values()) or audit.low_confidence_hashes:
        return FreeTextRejected(reason="pii_detected")
    return FreeTextAccepted()


# ---------------------------------------------------------------------------
# Storage models
# ---------------------------------------------------------------------------


class SessionStudentResponse(Base):
    """Raw per-student response row (base AC3, amendment #2).

    Only ever written by `record_response` below when the session's
    retention tier allows `SessionDataCategory.RAW_RESPONSES`
    (pseudonymous/identifiable) -- nothing else in this codebase should
    insert this table directly.

    Field shape deliberately mirrors `effectiveness-loop/el-001`'s
    `StudentAttemptRecord` (`services/gateway/outcome_models.py`):
    `student_pseudonym` + `kc_ids: list[str]` + `correct` -- so a future
    adapter that makes the effectiveness loop real can read this table as
    input without a reshape, instead of this becoming a second, incompatible
    capture format.
    """

    __tablename__ = "session_student_responses"
    __table_args__ = (
        Index("ix_session_student_responses_session_id", "session_id"),
        Index("ix_session_student_responses_student_pseudonym", "student_pseudonym"),
        {"schema": "public"},
    )

    response_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    interaction_id: Mapped[str] = mapped_column(String(80), nullable=False)
    student_pseudonym: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    kc_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SessionResponseAggregate(Base):
    """Class-concept/misconception rollup counters (base AC4).

    One row per (session_id, interaction_id), incremented on every response
    as long as the tier allows `SessionDataCategory.AGGREGATES` at all (every
    tier except `NONE`) -- so aggregate-tier sessions (the K-12 default,
    TSP-01 AC4) get real default analytics without ever persisting a raw
    per-student response.
    """

    __tablename__ = "session_response_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "interaction_id",
            name="uq_session_response_aggregates_session_interaction",
        ),
        Index("ix_session_response_aggregates_session_id", "session_id"),
        {"schema": "public"},
    )

    aggregate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    interaction_id: Mapped[str] = mapped_column(String(80), nullable=False)
    kc_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )


# ---------------------------------------------------------------------------
# Response submission (base AC1/AC2/AC3, retention-gated write path)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResponseAccepted:
    kind: ResponseKind
    raw_response_persisted: bool


@dataclass(frozen=True, slots=True)
class ResponseRejected:
    reason: str


type SubmitResponseResult = ResponseAccepted | ResponseRejected


async def record_response(
    db: AsyncSession,
    *,
    response_id: str,
    session_id: str,
    interaction_id: str,
    retention_tier: RetentionTier,
    kind: ResponseKind,
    payload: dict[str, Any],
    student_pseudonym: str,
    kc_ids: list[str] | None = None,
    correct: bool | None = None,
    interaction_allows_free_text: bool = False,
    session_allows_free_text: bool = False,
) -> SubmitResponseResult:
    """Validate, gate, and (fail-closed, per retention tier) persist one response.

    - `NONE` tier: nothing is persisted at all -- the session runs
      ephemerally (TSP-01 AC4).
    - `AGGREGATE` tier (K-12 default): only `SessionResponseAggregate`
      increments; no raw row is ever written.
    - `PSEUDONYMOUS`/`IDENTIFIABLE` tier: the aggregate increments *and* a
      raw `SessionStudentResponse` row is written.

    Caller resolves `correct` (against the interaction's answer key) and
    `kc_ids` (from the interaction's tagging, when derivable) upstream --
    this module intentionally does not couple to `SlideDeckInteraction`'s
    exact shape, matching `teaching_session.models`' existing stance on
    SDTF-01/06.
    """
    kc_ids = list(kc_ids or [])
    shape_error = _validate_payload(kind, payload)
    if shape_error is not None:
        return ResponseRejected(reason=shape_error)

    if kind is ResponseKind.FREE_TEXT:
        gate_result = gate_free_text(
            payload.get("text", ""),
            interaction_allows_free_text=interaction_allows_free_text,
            session_allows_free_text=session_allows_free_text,
        )
        if isinstance(gate_result, FreeTextRejected):
            return ResponseRejected(reason=gate_result.reason)

    categories = allowed_data_categories_for_tier(retention_tier)
    if SessionDataCategory.AGGREGATES not in categories:
        return ResponseAccepted(kind=kind, raw_response_persisted=False)

    await _increment_aggregate(
        db, session_id=session_id, interaction_id=interaction_id, kc_ids=kc_ids, correct=correct,
    )

    raw_persisted = SessionDataCategory.RAW_RESPONSES in categories
    if raw_persisted:
        db.add(SessionStudentResponse(
            response_id=response_id,
            session_id=session_id,
            interaction_id=interaction_id,
            student_pseudonym=student_pseudonym,
            kind=kind.value,
            kc_ids=kc_ids,
            payload=payload,
            correct=correct,
        ))
        await db.flush()

    return ResponseAccepted(kind=kind, raw_response_persisted=raw_persisted)


async def _increment_aggregate(
    db: AsyncSession,
    *,
    session_id: str,
    interaction_id: str,
    kc_ids: list[str],
    correct: bool | None,
) -> None:
    result = await db.execute(
        select(SessionResponseAggregate).where(
            SessionResponseAggregate.session_id == session_id,
            SessionResponseAggregate.interaction_id == interaction_id,
        ),
    )
    aggregate = result.scalar_one_or_none()
    if aggregate is None:
        # attempt_count/correct_count are passed explicitly (not left to the
        # column default) -- SQLAlchemy's `default=0` only applies at flush
        # time, so the in-memory attribute would still be `None` for the
        # `+= 1` below.
        aggregate = SessionResponseAggregate(
            aggregate_id=f"agg-{uuid4()}",
            session_id=session_id,
            interaction_id=interaction_id,
            kc_ids=kc_ids,
            attempt_count=0,
            correct_count=0,
        )
        db.add(aggregate)
    aggregate.attempt_count += 1
    if correct:
        aggregate.correct_count += 1
    await db.flush()


async def get_session_aggregates(
    db: AsyncSession, *, session_id: str,
) -> list[SessionResponseAggregate]:
    result = await db.execute(
        select(SessionResponseAggregate).where(SessionResponseAggregate.session_id == session_id),
    )
    return list(result.scalars().all())


async def get_session_raw_responses(
    db: AsyncSession, *, session_id: str,
) -> list[SessionStudentResponse]:
    result = await db.execute(
        select(SessionStudentResponse).where(SessionStudentResponse.session_id == session_id),
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Default analytics: class-concept/misconception aggregate (base AC4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MisconceptionRollupRow:
    """One class-concept/misconception bucket -- never a per-student breakdown."""

    key: str  # a kc_id, or f"interaction:{interaction_id}" when no kc_ids are tagged
    attempt_count: int
    correct_count: int

    @property
    def incorrect_count(self) -> int:
        return self.attempt_count - self.correct_count


def class_concept_rollup(
    aggregates: list[SessionResponseAggregate],
) -> list[MisconceptionRollupRow]:
    """Default analytics (base AC4): class-level, concept-grouped, never per-student.

    Groups by `kc_id` when an aggregate row carries any; falls back to the
    interaction itself when it carries none -- `SlideDeckInteraction` has no
    `kc_ids` field yet (see `teaching_session.models`'s SDTF-01 note), so
    this fallback is today's common case, not a corner case.
    """
    buckets: dict[str, MisconceptionRollupRow] = {}
    for row in aggregates:
        keys = row.kc_ids or [f"interaction:{row.interaction_id}"]
        for key in keys:
            existing = buckets.get(key)
            if existing is None:
                buckets[key] = MisconceptionRollupRow(
                    key=key, attempt_count=row.attempt_count, correct_count=row.correct_count,
                )
            else:
                buckets[key] = MisconceptionRollupRow(
                    key=key,
                    attempt_count=existing.attempt_count + row.attempt_count,
                    correct_count=existing.correct_count + row.correct_count,
                )
    return sorted(buckets.values(), key=lambda row: row.key)


# ---------------------------------------------------------------------------
# Gated drill-down (base AC5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StudentDrillDownRow:
    student_pseudonym: str
    interaction_id: str
    kc_ids: list[str]
    correct: bool | None


@dataclass(frozen=True, slots=True)
class DrillDownAccepted:
    rows: list[StudentDrillDownRow]


@dataclass(frozen=True, slots=True)
class DrillDownRejected:
    reason: str  # "retention_tier_does_not_allow_drill_down"


type DrillDownResult = DrillDownAccepted | DrillDownRejected


def student_drill_down(
    responses: list[SessionStudentResponse], *, retention_tier: RetentionTier,
) -> DrillDownResult:
    """Group/individual drill-down (base AC5) -- gated to pseudonymous/identifiable only.

    `NONE`/`AGGREGATE` tiers have no raw rows to drill into in the first
    place; this check turns that structural fact into an explicit, testable
    policy instead of an accident of what happens to be in the table.
    """
    if SessionDataCategory.RAW_RESPONSES not in allowed_data_categories_for_tier(retention_tier):
        return DrillDownRejected(reason="retention_tier_does_not_allow_drill_down")
    return DrillDownAccepted(rows=[
        StudentDrillDownRow(
            student_pseudonym=response.student_pseudonym,
            interaction_id=response.interaction_id,
            kc_ids=list(response.kc_ids),
            correct=response.correct,
        )
        for response in responses
    ])


# ---------------------------------------------------------------------------
# Gamification (amendment #1) -- non-competitive, opt-in via teacher memory
# ---------------------------------------------------------------------------


class GamificationMode(StrEnum):
    """Never a ranked/leaderboard mode -- only these two, or disabled."""

    DISABLED = "disabled"
    PRIVATE_PER_STUDENT = "private_per_student"
    CLASS_COLLECTIVE = "class_collective"


def gamification_mode_from_preference(preference: dict[str, Any] | None) -> GamificationMode:
    """Resolve a teacher's stored preference (see `teacher_memory.read_gamification_preference`).

    Fail-closed: a missing, disabled, or unrecognized value all resolve to
    `DISABLED` -- there is no third "legacy leaderboard" mode to fall back to.
    """
    if not preference or not preference.get("enabled"):
        return GamificationMode.DISABLED
    try:
        return GamificationMode(preference.get("mode", GamificationMode.DISABLED.value))
    except ValueError:
        return GamificationMode.DISABLED


def private_student_points(
    responses: list[SessionStudentResponse], *, student_pseudonym: str,
) -> int:
    """One student's own point total. Never returns another student's data or a ranked list."""
    return sum(
        1 for response in responses
        if response.student_pseudonym == student_pseudonym and response.correct
    )


def class_collective_points(aggregates: list[SessionResponseAggregate]) -> int:
    """Whole-class collective total -- a single number, never broken out per student."""
    return sum(aggregate.correct_count for aggregate in aggregates)
