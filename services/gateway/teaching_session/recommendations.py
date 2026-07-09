"""Teacher-approved post-lesson recommendations (TSP-07 AC4-6).

Candidates are generated from TSP-05's `class_concept_rollup` aggregate --
never raw per-student responses -- and always start `PENDING`. Nothing in
this module calls into real content generation until `approve_recommendation`
runs, and that function requires the caller to already hold an explicit
teacher approval (there is no auto-generate path). Generation itself reuses
`packages.agents.teaching_pack.generate_one_artifact` -- the same entrypoint
regular teaching-pack artifacts go through -- rather than a separate
auto-generation silo.

The evidence record (delivery mode + retention mode + recommendation
decision) reuses TSP-01's `SessionAuditEvent` table rather than adding a new
one: it already exists for exactly this "who/what/when of a
consent/access decision" shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Index, String, select
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base, utc_now
from services.gateway.teaching_session.models import DeliveryMode, RetentionTier, SessionAuditEvent
from services.gateway.teaching_session.responses import MisconceptionRollupRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from packages.agents.teaching_pack.generate_one_artifact import (
        GenerateOneArtifactPayload,
        GenerateOneArtifactResult,
    )

# ---------------------------------------------------------------------------
# Candidate generation (pure, cites aggregate evidence only)
# ---------------------------------------------------------------------------


class RecommendationKind(StrEnum):
    """The four follow-up shapes named in ADR-046 / TSP-07's base issue."""

    RETEACH_MINI_DECK = "reteach_mini_deck"
    PRACTICE_WORKSHEET = "practice_worksheet"
    HOMEWORK = "homework"
    NEXT_LESSON_ADJUSTMENT = "next_lesson_adjustment"


# Which existing `ArtifactContent.artifact_type` a recommendation kind
# generates through -- reuses the teaching-pack contract's existing literals
# (common/contracts/artifact.py) instead of inventing new ones.
RECOMMENDATION_ARTIFACT_TYPES: Final[dict[RecommendationKind, str]] = {
    RecommendationKind.RETEACH_MINI_DECK: "slide_deck",
    RecommendationKind.PRACTICE_WORKSHEET: "worksheet",
    RecommendationKind.HOMEWORK: "drill",
    RecommendationKind.NEXT_LESSON_ADJUSTMENT: "roadmap",
}

# ponytail: below what class accuracy a concept counts as "weak" enough to
# warrant reteach/practice/homework candidates. A flat threshold, not a
# per-subject/grade model -- revisit if teacher feedback shows this fires
# too eagerly or too rarely for a given grade band.
_WEAK_CONCEPT_ACCURACY_THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    kind: RecommendationKind
    evidence_keys: list[str]
    rationale: str


def generate_recommendation_candidates(
    rollup: list[MisconceptionRollupRow],
) -> list[RecommendationCandidate]:
    """Post-lesson recommendation candidates citing aggregate/concept evidence (base AC1).

    `evidence_keys` are `MisconceptionRollupRow.key` values (kc_ids or
    `interaction:<id>` fallbacks) -- concept-level, never a student
    pseudonym or raw response. Returns `[]` when there is nothing to
    recommend from (no aggregate rows at all).
    """
    if not rollup:
        return []

    weak = [
        row for row in rollup
        if row.attempt_count > 0
        and (row.correct_count / row.attempt_count) < _WEAK_CONCEPT_ACCURACY_THRESHOLD
    ]

    candidates: list[RecommendationCandidate] = []
    if weak:
        weak_keys = [row.key for row in weak]
        candidates.append(RecommendationCandidate(
            kind=RecommendationKind.RETEACH_MINI_DECK,
            evidence_keys=weak_keys,
            rationale=f"{len(weak)} concept(s) below {_WEAK_CONCEPT_ACCURACY_THRESHOLD:.0%} class accuracy",
        ))
        candidates.append(RecommendationCandidate(
            kind=RecommendationKind.PRACTICE_WORKSHEET,
            evidence_keys=weak_keys,
            rationale="Targeted practice for the same weak concept(s)",
        ))
        candidates.append(RecommendationCandidate(
            kind=RecommendationKind.HOMEWORK,
            evidence_keys=weak_keys,
            rationale="Independent follow-up on the same weak concept(s)",
        ))
    candidates.append(RecommendationCandidate(
        kind=RecommendationKind.NEXT_LESSON_ADJUSTMENT,
        evidence_keys=[row.key for row in rollup],
        rationale="Pacing/sequencing review based on the full class rollup",
    ))
    return candidates


# ---------------------------------------------------------------------------
# Pending-recommendation storage (teacher-approval gate)
# ---------------------------------------------------------------------------


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"


class SessionRecommendation(Base):
    """A recommendation candidate awaiting (or holding) teacher approval.

    Never generated from automatically -- `approve_recommendation` is the
    only function that transitions a row to `APPROVED` and, in the same call,
    invokes real generation. Nothing reads this table to auto-generate.
    """

    __tablename__ = "session_recommendations"
    __table_args__ = (
        Index("ix_session_recommendations_session_id", "session_id"),
        {"schema": "public"},
    )

    recommendation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RecommendationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


async def create_pending_recommendation(
    db: AsyncSession, *, session_id: str, candidate: RecommendationCandidate,
) -> SessionRecommendation:
    """Persist one candidate as `PENDING` -- never auto-approved."""
    recommendation = SessionRecommendation(
        recommendation_id=f"rec-{uuid4()}",
        session_id=session_id,
        kind=candidate.kind.value,
        evidence_keys=candidate.evidence_keys,
        rationale=candidate.rationale,
    )
    db.add(recommendation)
    await db.flush()
    return recommendation


async def approve_recommendation(
    db: AsyncSession,
    *,
    recommendation_id: str,
    approver_id: str,
    delivery_mode: DeliveryMode,
    retention_tier: RetentionTier,
    generate_payload: GenerateOneArtifactPayload,
) -> GenerateOneArtifactResult:
    """Approve a pending recommendation, then generate through the real pathway.

    This is the *only* function in this module that calls
    `generate_one_artifact` -- there is no other path from a recommendation
    candidate to generated content. Raises `OMCError` (VALIDATION_ERROR) if
    the recommendation doesn't exist, is already approved, or the caller's
    `generate_payload["artifact_type"]` doesn't match the artifact type this
    recommendation kind is supposed to generate.
    """
    # Imported here, not at module load, to keep this module importable
    # without pulling in the full teaching-pack agent graph for tests that
    # only exercise candidate generation/approval bookkeeping.
    from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact

    result = await db.execute(
        select(SessionRecommendation).where(
            SessionRecommendation.recommendation_id == recommendation_id,
        ),
    )
    recommendation = result.scalar_one_or_none()
    if recommendation is None:
        raise OMCError(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Recommendation {recommendation_id!r} not found",
        )
    if recommendation.status != RecommendationStatus.PENDING.value:
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Recommendation {recommendation_id!r} is not pending",
            details=[{"field": "status", "reason": "recommendation_not_pending"}],
        )

    kind = RecommendationKind(recommendation.kind)
    expected_artifact_type = RECOMMENDATION_ARTIFACT_TYPES[kind]
    if generate_payload["artifact_type"] != expected_artifact_type:
        raise OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=(
                f"Recommendation kind {kind.value!r} generates "
                f"{expected_artifact_type!r}, got {generate_payload['artifact_type']!r}"
            ),
            details=[{"field": "artifact_type", "reason": "artifact_type_mismatch"}],
        )

    recommendation.status = RecommendationStatus.APPROVED.value
    recommendation.approved_at = utc_now()
    recommendation.approved_by = approver_id

    db.add(SessionAuditEvent(
        event_id=f"audit-{uuid4()}",
        session_id=recommendation.session_id,
        actor_id=approver_id,
        action="recommendation_approved",
        event_metadata={
            "recommendation_id": recommendation_id,
            "kind": kind.value,
            "delivery_mode": delivery_mode.value,
            "retention_tier": retention_tier.value,
            "evidence_keys": recommendation.evidence_keys,
        },
    ))
    await db.flush()

    return await generate_one_artifact(generate_payload)
