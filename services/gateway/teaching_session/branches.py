"""Precomputed live-session branches + teacher-only AI branch suggestions (TSP-06, ADR-046).

A "branch" is a small alternate-content variant (reteach, hint, simpler
example, challenge, extra practice) a teacher can switch to mid-class in
response to what the class is showing -- see `teaching_session_live.py`'s
`/branch` route, which already records the `branch_selected` significant
event (TSP-03).

Two ways a branch's content comes to exist:

1. **Precomputed** (the zero-latency default, TSP-06 amendment): authored
   ahead of class, quality-gated once at creation time, and simply looked up
   by `list_precomputed_branches` during class -- no LLM call on the
   critical path.
2. **On-the-fly AI** (the fallback): the teacher-triggered "generate a new
   suggestion" action reuses SDE-08's *exact* pipeline
   (`block_rewrite_llm.resolve_rewrite_instruction` +
   `generate_slide_deck_block_rewrite`) -- see
   `services/gateway/routers/teaching_session_live.py`'s
   `/branch-suggestions` (generate, never persists) and
   `/branch-suggestions/apply` (teacher-approved -> persists through the
   SAME `create_precomputed_branch` quality gate below, then records
   `branch_selected` with `source="ai_generated"`) routes. There is
   deliberately no separate live-generation system (TSP-06 amendment #1).

Content-safety boundary (TSP-06 base ACs): a `/branch-suggestions` response
is handed straight back to the calling teacher's own HTTP request -- it is
never written to `PrecomputedBranch`, never touches the session event log,
and is therefore structurally unreachable from the SSE broadcast
(`live_sync.publish_event`) any student/display connection subscribes to.
The ONLY path from an AI-drafted suggestion to `branch_selected` visibility
is `/branch-suggestions/apply`, which re-runs the same quality gate a
precomputed branch must pass and requires the teacher's explicit approval
(the reused `AiBlockRewriteConfirmModal`'s "Apply" click) to reach it at all.

ponytail: branch content is one alternate text block (title/body), not a
full alternate slide/interaction graph -- matches the granularity SDE-08's
block-rewrite pipeline already produces and keeps the quality gate a
self-contained synthetic one-slide/one-block deck (no dependency on loading
the *real* deck's `SlideDeckData` into `teaching_session`, which has no
established fetch path today -- see `models.py`'s "kept as opaque strings on
purpose" docstring). Upgrade to a real alternate-slide/interaction shape if
a branch ever needs more than swapped text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from common.contracts.slide_deck import (
    SlideDeckAccessibility,
    SlideDeckBlock,
    SlideDeckData,
    SlideDeckMediaPolicy,
    SlideDeckProgression,
    SlideDeckSlide,
    SlideDeckSurface,
    SlideDeckSurfaces,
)
from packages.agents.slide_deck_engine.policies import DensityBudgetPolicy
from packages.agents.slide_deck_engine.quality import (
    validate_registry_membership,
    validate_teacher_only_separation,
)
from services.gateway.models import Base, utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from packages.agents.slide_deck_engine.models import SlideDeckValidationReport


class BranchContentType(StrEnum):
    """The five branch content types (TSP-06 base AC1)."""

    RETEACH = "reteach"
    HINT = "hint"
    SIMPLER_EXAMPLE = "simpler_example"
    CHALLENGE = "challenge"
    EXTRA_PRACTICE = "extra_practice"


class BranchSource(StrEnum):
    """How a branch's content came to exist -- recorded on both the row and
    the `branch_selected` event payload (TSP-06 "recorded as a session event")."""

    PRECOMPUTED = "precomputed"
    AI_GENERATED = "ai_generated"


@dataclass(frozen=True, slots=True)
class BranchRejected:
    """Fail-closed result: the branch never reaches storage / student visibility."""

    reason: str  # "quality_gate_failed"
    reports: list[SlideDeckValidationReport]


class PrecomputedBranch(Base):
    """A quality-gated branch variant attached to a deck/slide (+ optional interaction).

    Rows are only ever created via `create_precomputed_branch` below, which
    is the sole path that runs the quality gate -- there is no other insert
    path, so "every row passed the gate" is a structural invariant, not a
    convention.
    """

    __tablename__ = "precomputed_branches"
    __table_args__ = (
        Index("ix_precomputed_branches_deck_id_slide_id", "deck_id", "slide_id"),
        {"schema": "public"},
    )

    branch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    deck_id: Mapped[str] = mapped_column(String(80), nullable=False)
    slide_id: Mapped[str] = mapped_column(String(80), nullable=False)
    interaction_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    branch_type: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default=BranchSource.PRECOMPUTED.value,
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# ---------------------------------------------------------------------------
# Quality/projection gate -- the SAME shape real slide content passes
# ---------------------------------------------------------------------------

_BRANCH_SLIDE_LAYOUT = "content"
_BRANCH_BLOCK_TYPE = "paragraph"
_MAX_BLOCKS_PER_SLIDE = 4
_MAX_INTERACTIONS_PER_SLIDE = 2


def _synthetic_branch_deck(body: str) -> SlideDeckData:
    """One self-contained, minimal-but-valid deck wrapping exactly one branch block."""
    surface = SlideDeckSurface(mode="presentation", export_format="html")
    return SlideDeckData(
        deck_id="branch-quality-check",
        title="Branch content quality check",
        locale="en",
        surfaces=SlideDeckSurfaces(student=surface, teacher=surface, print=surface),
        slides=[
            SlideDeckSlide(
                slide_id="branch-preview-slide",
                title="Branch preview",
                layout=_BRANCH_SLIDE_LAYOUT,
                progression=SlideDeckProgression(step_index=1, reveal_policy="all_at_once"),
                blocks=[
                    SlideDeckBlock(
                        block_id="branch-body", block_type=_BRANCH_BLOCK_TYPE, body=body,
                    ),
                ],
            ),
        ],
        accessibility=SlideDeckAccessibility(reading_level="grade_appropriate", language="en"),
        media_policy=SlideDeckMediaPolicy(
            default_tier="packaged", online_optional_allowed=False, fallback_required=True,
        ),
    )


def validate_branch_quality(body: str) -> list[SlideDeckValidationReport]:
    """Run the same registry/density/teacher-only-separation gates real slide
    content passes (`quality.py`) against a synthetic one-slide/one-block deck
    wrapping this branch's body.

    Deliberately reuses `validate_registry_membership` and
    `validate_teacher_only_separation` verbatim, and `DensityBudgetPolicy`
    (the per-slide density check `audit_density_and_accessibility` composes)
    directly rather than that whole-deck audit routine -- its
    `PageCountPolicy`/`evaluate_deck_shape` checks are deck-wide slide-*count*
    concerns that don't apply to a single-branch fragment.
    """
    deck = _synthetic_branch_deck(body)
    return [
        *validate_registry_membership(deck),
        DensityBudgetPolicy(
            max_blocks_per_slide=_MAX_BLOCKS_PER_SLIDE,
            max_interactions_per_slide=_MAX_INTERACTIONS_PER_SLIDE,
        ).evaluate(deck),
        validate_teacher_only_separation(deck),
    ]


def _quality_failures(reports: list[SlideDeckValidationReport]) -> list[SlideDeckValidationReport]:
    return [report for report in reports if not report.passed]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


async def create_precomputed_branch(
    db: AsyncSession,
    *,
    deck_id: str,
    slide_id: str,
    branch_type: BranchContentType,
    label: str,
    body: str,
    created_by: str,
    interaction_id: str | None = None,
    source: BranchSource = BranchSource.PRECOMPUTED,
) -> PrecomputedBranch | BranchRejected:
    """Quality-gate `body`, then persist -- fail closed on any gate failure.

    The one insert path both the teacher-prep flow (`source=PRECOMPUTED`) and
    the AI-suggestion-approval flow (`source=AI_GENERATED`, called from
    `/branch-suggestions/apply`) share, so an AI-drafted branch is held to
    exactly the same bar as a hand-authored one before it can ever become
    student-visible (TSP-06 base AC6).
    """
    reports = validate_branch_quality(body)
    failures = _quality_failures(reports)
    if failures:
        return BranchRejected(reason="quality_gate_failed", reports=failures)

    branch = PrecomputedBranch(
        branch_id=f"branch-{uuid4()}",
        deck_id=deck_id,
        slide_id=slide_id,
        interaction_id=interaction_id,
        branch_type=branch_type.value,
        label=label,
        body=body,
        source=source.value,
        created_by=created_by,
    )
    db.add(branch)
    await db.flush()
    return branch


async def list_precomputed_branches(
    db: AsyncSession, *, deck_id: str, slide_id: str,
) -> list[PrecomputedBranch]:
    """The zero-latency default the cockpit surfaces first (TSP-06 amendment #2)."""
    result = await db.execute(
        select(PrecomputedBranch)
        .where(PrecomputedBranch.deck_id == deck_id, PrecomputedBranch.slide_id == slide_id)
        .order_by(PrecomputedBranch.created_at),
    )
    return list(result.scalars().all())


async def get_precomputed_branch(db: AsyncSession, *, branch_id: str) -> PrecomputedBranch | None:
    return await db.get(PrecomputedBranch, branch_id)
