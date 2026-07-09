"""Retention-tier policy for TeachingSession (TSP-01 AC3/4/5/6, amendments #1/#3/#4).

Retention *tier* governs how identifying stored session data may be. Data
*category* (`SessionDataCategory`) is the orthogonal axis of what kind of
data exists. `allowed_data_categories_for_tier` is where the two meet: the
single place that says, e.g., "aggregate tier never persists raw responses".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from services.gateway.teaching_session.models import (
    RetentionTier,
    SessionDataCategory,
    SessionStatus,
    TeachingSession,
)

# ---------------------------------------------------------------------------
# Tier selection validation (called once, at session creation)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetentionSelectionAccepted:
    tier: RetentionTier


@dataclass(frozen=True, slots=True)
class RetentionSelectionRejected:
    tier: RetentionTier
    reason: str


type RetentionSelectionResult = RetentionSelectionAccepted | RetentionSelectionRejected

_IDENTITY_BEARING_TIERS = frozenset({RetentionTier.PSEUDONYMOUS, RetentionTier.IDENTIFIABLE})


def validate_retention_selection(
    *,
    tier: RetentionTier,
    class_id: str | None,
    identifiable_acknowledged: bool,
) -> RetentionSelectionResult:
    """Validate a retention tier choice at session creation.

    - pseudonymous/identifiable require a real, non-empty `class_id`
      (TSP-01 amendment #4) -- never for an anonymous open-join room.
    - identifiable additionally requires an explicit acknowledgment; the
      caller is responsible for persisting that acknowledgment to the audit
      trail (`SessionAuditEvent`) alongside the session, in the same unit of
      work (TSP-01 amendment #3; see `teaching_session.service.create_session`).
    """
    if tier in _IDENTITY_BEARING_TIERS and not class_id:
        return RetentionSelectionRejected(
            tier=tier,
            reason="class_id_required_for_identity_bearing_tier",
        )
    if tier is RetentionTier.IDENTIFIABLE and not identifiable_acknowledged:
        return RetentionSelectionRejected(
            tier=tier,
            reason="identifiable_tier_requires_explicit_acknowledgment",
        )
    return RetentionSelectionAccepted(tier=tier)


# ---------------------------------------------------------------------------
# Data category separation (TSP-01 AC6)
# ---------------------------------------------------------------------------

_ALLOWED_CATEGORIES: dict[RetentionTier, frozenset[SessionDataCategory]] = {
    RetentionTier.NONE: frozenset({
        SessionDataCategory.TEACHER_REFLECTIONS,
        SessionDataCategory.AI_SUGGESTIONS,
    }),
    RetentionTier.AGGREGATE: frozenset({
        SessionDataCategory.EVENTS,
        SessionDataCategory.AGGREGATES,
        SessionDataCategory.TEACHER_REFLECTIONS,
        SessionDataCategory.AI_SUGGESTIONS,
        SessionDataCategory.EXPORTS,
    }),
    RetentionTier.PSEUDONYMOUS: frozenset({
        SessionDataCategory.EVENTS,
        SessionDataCategory.AGGREGATES,
        SessionDataCategory.RAW_RESPONSES,
        SessionDataCategory.TEACHER_REFLECTIONS,
        SessionDataCategory.AI_SUGGESTIONS,
        SessionDataCategory.EXPORTS,
    }),
    RetentionTier.IDENTIFIABLE: frozenset(SessionDataCategory),
}


def allowed_data_categories_for_tier(tier: RetentionTier) -> frozenset[SessionDataCategory]:
    """Which data categories a session at *tier* is allowed to persist.

    ``RAW_RESPONSES`` never appears for `NONE`/`AGGREGATE` -- that is the
    K-12-safe default this whole module exists to enforce (TSP-01 AC4).
    """
    return _ALLOWED_CATEGORIES[tier]


# ---------------------------------------------------------------------------
# Policy visibility for teacher/admin surfaces and evidence (TSP-01 AC5)
# ---------------------------------------------------------------------------

_TIER_LABELS: dict[RetentionTier, str] = {
    RetentionTier.NONE: "No student data",
    RetentionTier.AGGREGATE: "Aggregate / class-level (K-12 default)",
    RetentionTier.PSEUDONYMOUS: "Pseudonymous per-student",
    RetentionTier.IDENTIFIABLE: "Identifiable per-student",
}

_TIER_DESCRIPTIONS: dict[RetentionTier, str] = {
    RetentionTier.NONE: "Nothing student-facing is persisted; the session runs ephemerally.",
    RetentionTier.AGGREGATE: (
        "Only class-level aggregates and lifecycle events are kept; no raw per-student responses."
    ),
    RetentionTier.PSEUDONYMOUS: (
        "Raw responses are kept under a per-session pseudonym, never a real student identity."
    ),
    RetentionTier.IDENTIFIABLE: (
        "Raw responses are kept tied to a real student identity. Requires an explicit, "
        "audited acknowledgment and a real class."
    ),
}


@dataclass(frozen=True, slots=True)
class RetentionPolicyDescription:
    tier: RetentionTier
    label: str
    description: str
    allowed_categories: frozenset[SessionDataCategory]


def describe_retention_policy(tier: RetentionTier) -> RetentionPolicyDescription:
    """Human-readable retention summary for teacher/admin surfaces and evidence.

    Satisfies TSP-01 AC5 ("retention policy is visible ... and can be
    included in evidence") as a pure, serializable function rather than UI --
    this slice builds the data model and policy, not the cockpit/evidence
    surfaces that will call this.
    """
    return RetentionPolicyDescription(
        tier=tier,
        label=_TIER_LABELS[tier],
        description=_TIER_DESCRIPTIONS[tier],
        allowed_categories=allowed_data_categories_for_tier(tier),
    )


# ---------------------------------------------------------------------------
# Purge predicate (TSP-01 amendment #1)
# ---------------------------------------------------------------------------

# Retention window per tier, in days, applied from the session's terminal
# timestamp. More-identifying tiers get *shorter* windows -- mirrors
# ADR-034's student_evidence=30-day rule and `services/gateway/retention.py`'s
# shape (that module's `is_expired` hardcodes real wall-clock time via
# `datetime.now(UTC)` with no injectable `now`, which would make this
# predicate untestable at exact day boundaries; the arithmetic below is
# equivalent but takes `now` explicitly).
_RETENTION_WINDOW_DAYS: dict[RetentionTier, int] = {
    RetentionTier.NONE: 0,
    RetentionTier.IDENTIFIABLE: 30,
    RetentionTier.PSEUDONYMOUS: 90,
    RetentionTier.AGGREGATE: 180,
}

_TERMINAL_STATUSES = frozenset({SessionStatus.ENDED, SessionStatus.ARCHIVED, SessionStatus.EXPIRED})


def is_prunable(session: TeachingSession, now: datetime) -> bool:
    """Fail-closed, session-scoped purge predicate (TSP-01 amendment #1).

    Deliberately mirrors the *shape* of OPS-07's not-yet-built
    `is_prunable(run, artifacts, now) -> bool` predicate (see
    `.scratch/scalability-elite-modules/issues/OPS-07-data-lifecycle-retention.md`)
    without depending on it, so a future consolidation is a refactor, not a
    rewrite -- meant to be called by a future scheduled sweeper, which this
    slice does not build.

    Default-deny: every allow path is an explicit condition below; a session
    that is not yet terminal, has no terminal timestamp, or has an unknown
    retention tier is never prunable.
    """
    if session.status not in _TERMINAL_STATUSES:
        return False

    terminal_at = session.archived_at or session.ended_at or session.expired_at
    if terminal_at is None:
        return False

    window_days = _RETENTION_WINDOW_DAYS.get(session.retention_tier)
    if window_days is None:
        return False
    if window_days == 0:
        return True

    return now >= terminal_at + timedelta(days=window_days)
