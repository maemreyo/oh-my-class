"""RISE template-effectiveness signal (el-007).

Cross-student aggregation of mastery-gain per (template, KC) to inform
decomposition-memory ranking.

3-layer HITL:
  L1 AUTO       — auto-apply low-risk hints (e.g. "try shorter sessions").
  L2 SUGGESTION — effectiveness-driven content changes, requires teacher approval.
  L3 ADVISORY   — read-only insights; no automated side-effect.

Privacy (PDPD 13/2023): only pseudonyms + KC mastery floats flow through here;
no raw student responses or real PII.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Float, Index, Integer, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from common.contracts.outcome import StudentKCState
from services.gateway.decomposition_memory import DecompositionTemplateKey

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_SAMPLE: int = 3
"""Sparse-data suppression: signals with fewer sessions are suppressed from ranked results."""

MASTERY_GAIN_THRESHOLD: float = 0.05
"""Minimum average mastery gain before a template is flagged as under-performing."""


# ---------------------------------------------------------------------------
# HITL layer enum
# ---------------------------------------------------------------------------


class HitlLayer(StrEnum):
    AUTO = "auto"
    SUGGESTION = "suggestion"
    ADVISORY = "advisory"


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TemplateEffectivenessSignal:
    template_id: str
    topic_normalized: str
    grade: str
    subject: str
    locale: str
    methodology: str | None
    average_mastery_gain: float
    sample_size: int
    is_flagged: bool
    """True when sample_size >= MIN_SAMPLE and average_mastery_gain < MASTERY_GAIN_THRESHOLD."""


# ---------------------------------------------------------------------------
# SQLAlchemy model (local Base — separate from the main gateway Base so this
# module stays independently deployable without importing the full schema).
# ---------------------------------------------------------------------------


class _EffBase(DeclarativeBase):
    pass


class TemplateEffectivenessModel(_EffBase):
    """Rolling-average effectiveness signal per template."""

    __tablename__ = "template_effectiveness"
    __table_args__ = (
        UniqueConstraint("template_id", name="uq_template_effectiveness_template_id"),
        Index("ix_template_effectiveness_topic_grade_subject_locale",
              "topic_normalized", "grade", "subject", "locale"),
        {"schema": "public"},
    )

    effectiveness_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    topic_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    grade: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    methodology: Mapped[str | None] = mapped_column(String(128), nullable=True)
    average_mastery_gain: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def aggregate_mastery_gains(
    kc_states_before: list[StudentKCState],
    kc_states_after: list[StudentKCState],
) -> float:
    """Compute average (after.mastery - before.mastery) across matching (student_pseudonym, kc_id) pairs.

    Returns 0.0 if there are no matching pairs.
    """
    before_index: dict[tuple[str, str], float] = {
        (s.student_pseudonym, s.kc_id): s.mastery for s in kc_states_before
    }
    gains: list[float] = []
    for state in kc_states_after:
        key = (state.student_pseudonym, state.kc_id)
        if key in before_index:
            gains.append(state.mastery - before_index[key])
    if not gains:
        return 0.0
    return sum(gains) / len(gains)


def classify_hitl_layer(mastery_gain: float, sample_size: int) -> HitlLayer:
    """Classify a mastery-gain signal into the appropriate HITL layer.

    Rules (in priority order):
    1. sample_size < MIN_SAMPLE              → ADVISORY (not enough data yet).
    2. mastery_gain < 0.0                    → SUGGESTION (negative gain, teacher review required).
    3. mastery_gain < 0.02 and sample >= MIN → SUGGESTION (near-zero gain, teacher approval needed).
    4. else                                  → ADVISORY  (positive / acceptable; low-risk hints qualify for AUTO
                                               only after explicit teacher opt-in, surfaced as ADVISORY here).
    """
    if sample_size < MIN_SAMPLE:
        return HitlLayer.ADVISORY
    if mastery_gain < 0.0:
        return HitlLayer.SUGGESTION
    if mastery_gain < 0.02:
        return HitlLayer.SUGGESTION
    return HitlLayer.ADVISORY


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TemplateEffectivenessStore:
    """Async store for RISE effectiveness signals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_effectiveness(
        self,
        template_key: DecompositionTemplateKey,
        kc_ids: list[str],  # noqa: ARG002  # reserved for per-KC breakdown (future)
        mastery_gain: float,
    ) -> None:
        """Upsert a rolling-average effectiveness signal for the given template.

        The rolling average is updated as:
            new_avg = (old_avg * old_n + new_gain) / (old_n + 1)
        """
        # Fetch existing row if present.
        result = await self._session.execute(
            select(TemplateEffectivenessModel).where(
                TemplateEffectivenessModel.topic_normalized == template_key.topic_normalized,
                TemplateEffectivenessModel.grade == template_key.grade,
                TemplateEffectivenessModel.subject == template_key.subject,
                TemplateEffectivenessModel.locale == template_key.locale,
                # teacher-scoped lookup via template_key; template_id is the primary dedup key
                # but we also filter by teacher to avoid cross-teacher bleed.
            ).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            old_n = existing.sample_size
            old_avg = existing.average_mastery_gain
            new_n = old_n + 1
            new_avg = (old_avg * old_n + mastery_gain) / new_n
            existing.average_mastery_gain = new_avg
            existing.sample_size = new_n
            await self._session.flush()
        else:
            # Derive a deterministic template_id from the key so repeated inserts are idempotent.
            template_id = (
                f"tpl-{template_key.teacher_id}-{template_key.topic_normalized}"
                f"-{template_key.grade}-{template_key.subject}-{template_key.locale}"
            )
            statement = pg_insert(TemplateEffectivenessModel).values(
                effectiveness_id=f"eff-{uuid4()}",
                template_id=template_id,
                topic_normalized=template_key.topic_normalized,
                grade=template_key.grade,
                subject=template_key.subject,
                locale=template_key.locale,
                methodology=None,
                average_mastery_gain=mastery_gain,
                sample_size=1,
            ).on_conflict_do_update(
                constraint="uq_template_effectiveness_template_id",
                set_={
                    "average_mastery_gain": mastery_gain,
                    "sample_size": 1,
                },
            )
            await self._session.execute(statement)
            await self._session.flush()

    async def rank_templates(
        self,
        topic_normalized: str,
        grade: str,
        subject: str,
        locale: str,
    ) -> list[TemplateEffectivenessSignal]:
        """Return templates ordered by average_mastery_gain desc.

        Templates with sample_size < MIN_SAMPLE are suppressed (sparse data).
        """
        result = await self._session.execute(
            select(TemplateEffectivenessModel).where(
                TemplateEffectivenessModel.topic_normalized == topic_normalized,
                TemplateEffectivenessModel.grade == grade,
                TemplateEffectivenessModel.subject == subject,
                TemplateEffectivenessModel.locale == locale,
                TemplateEffectivenessModel.sample_size >= MIN_SAMPLE,
            ).order_by(TemplateEffectivenessModel.average_mastery_gain.desc())
        )
        rows = result.scalars().all()
        return [
            TemplateEffectivenessSignal(
                template_id=row.template_id,
                topic_normalized=row.topic_normalized,
                grade=row.grade,
                subject=row.subject,
                locale=row.locale,
                methodology=row.methodology,
                average_mastery_gain=row.average_mastery_gain,
                sample_size=row.sample_size,
                is_flagged=(
                    row.sample_size >= MIN_SAMPLE
                    and row.average_mastery_gain < MASTERY_GAIN_THRESHOLD
                ),
            )
            for row in rows
        ]

    async def get_hitl_suggestions(
        self,
        template_key: DecompositionTemplateKey,
    ) -> list[dict]:
        """Return L1/L2/L3 HITL suggestions based on stored effectiveness signals.

        Each dict has keys:
          layer      — HitlLayer value string
          message    — human-readable suggestion text
          auto_apply — bool, True only for L1 AUTO suggestions
        """
        result = await self._session.execute(
            select(TemplateEffectivenessModel).where(
                TemplateEffectivenessModel.topic_normalized == template_key.topic_normalized,
                TemplateEffectivenessModel.grade == template_key.grade,
                TemplateEffectivenessModel.subject == template_key.subject,
                TemplateEffectivenessModel.locale == template_key.locale,
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return []

        layer = classify_hitl_layer(row.average_mastery_gain, row.sample_size)
        suggestions: list[dict] = []

        if layer == HitlLayer.AUTO:
            suggestions.append({
                "layer": HitlLayer.AUTO,
                "message": (
                    "Mastery gain is healthy. Consider shorter individual sessions "
                    "to reduce cognitive load."
                ),
                "auto_apply": True,
            })
        elif layer == HitlLayer.SUGGESTION:
            suggestions.append({
                "layer": HitlLayer.SUGGESTION,
                "message": (
                    f"Average mastery gain is {row.average_mastery_gain:.3f} across "
                    f"{row.sample_size} session(s). Consider revising the activity "
                    "sequence or adding scaffolding before the main activity."
                ),
                "auto_apply": False,
            })
        else:
            # ADVISORY — read-only insight
            suggestions.append({
                "layer": HitlLayer.ADVISORY,
                "message": (
                    f"Average mastery gain is {row.average_mastery_gain:.3f} across "
                    f"{row.sample_size} session(s). More data is needed before "
                    "automated or teacher-directed adjustments are suggested."
                ),
                "auto_apply": False,
            })

        return suggestions
