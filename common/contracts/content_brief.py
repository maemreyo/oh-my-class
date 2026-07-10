"""The typed Content Brief: the only input a specialist receives (ADR-053, ADR-054).

Distinct from `TeachingBrief` (`common/contracts/teaching_brief.py`), which is
the teacher-facing intake. The Content Brief is derived by the orchestrator
from the Teaching Brief + approved Component Strategy + Research Brief, and
is what a specialist actually sees -- never the full run state, never
agent-to-agent chat. The schema is closed (`extra="forbid"`) so "specialists
receive only approved context" is a property enforced by the type, not a
convention a caller has to remember.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.run_contract import ArtifactType  # noqa: TC001

AnswerPolicy = Literal["none", "teacher_only", "derived"]
MethodologySource = Literal["teacher_pin", "strategy_recommendation", "default"]

DEFAULT_METHODOLOGY = "direct_instruction"


class ContentBrief(BaseModel):
    """Approved, bounded context for one artifact slot. Specialists may choose
    among `eligible_component_variants` (bounded specialist choice) but may not
    add objectives, widen scope, swap methodology, or use an unlisted learning
    move -- see `enforce_content_brief_compliance`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content_brief_id: str = Field(min_length=1, max_length=80)
    run_id: str = Field(min_length=1, max_length=64)
    artifact_type: ArtifactType
    objectives: list[str] = Field(min_length=1)
    scope: list[str] = Field(default_factory=list)
    methodology: str = Field(min_length=1, max_length=80)
    methodology_source: MethodologySource
    learning_moves: list[str] = Field(default_factory=list)
    eligible_component_variants: list[str] = Field(default_factory=list)
    terminology: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    answer_policy: AnswerPolicy = "none"
    dependency_document_ids: list[str] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)


def resolve_methodology(
    *,
    teacher_pin: str | None,
    strategy_recommendation: str | None,
    default: str = DEFAULT_METHODOLOGY,
) -> tuple[str, MethodologySource]:
    """Methodology precedence (ADR-053): a teacher's Teaching Brief pin always
    wins; otherwise the Component Strategy's recommendation; otherwise the
    governed default. A specialist may implement the resolved methodology but
    may never silently substitute another (see `enforce_content_brief_compliance`).
    """
    if teacher_pin is not None and teacher_pin.strip():
        return teacher_pin.strip(), "teacher_pin"
    if strategy_recommendation is not None and strategy_recommendation.strip():
        return strategy_recommendation.strip(), "strategy_recommendation"
    return default, "default"


def is_choice_within_bounds(brief: ContentBrief, chosen_variant: str) -> bool:
    """Bounded specialist choice: a variant is allowed only if the brief lists it,
    or the brief lists none at all (no variant menu was constrained for this slot)."""
    if not brief.eligible_component_variants:
        return True
    return chosen_variant in brief.eligible_component_variants
