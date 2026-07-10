"""Typed fill failures, strategy-change requests, and Content Brief compliance
enforcement (ADR-053, ADR-054).

A specialist that cannot fill its approved slot -- or believes the slot
itself is wrong -- must return one of the two typed outcomes below instead
of silently deviating. `enforce_content_brief_compliance` is the boundary
that turns "silently changed the plan" into a hard, typed error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from common.contracts.content_brief import ContentBrief

FillFailureReason = Literal[
    "objective_uncoverable",
    "scope_conflict",
    "missing_dependency",
    "methodology_unsupported",
    "insufficient_evidence",
]

StrategyChangeKind = Literal[
    "objective_change",
    "scope_change",
    "methodology_change",
    "learning_move_change",
]


class TypedFillFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_brief_id: str = Field(min_length=1, max_length=80)
    reason: FillFailureReason
    detail: str = Field(min_length=1, max_length=2_000)


class StrategyChangeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_brief_id: str = Field(min_length=1, max_length=80)
    change_kind: StrategyChangeKind
    rationale: str = Field(min_length=1, max_length=2_000)


class SpecialistOutputDeclaration(BaseModel):
    """What a specialist declares it produced, checked against the Content Brief
    that authorized it -- never trusted from the generated payload itself."""

    model_config = ConfigDict(frozen=True)

    methodology: str = Field(min_length=1, max_length=80)
    objectives_covered: list[str] = Field(default_factory=list)
    learning_moves_used: list[str] = Field(default_factory=list)


class SpecialistComplianceError(ValueError):
    """Raised instead of persisting specialist output that silently deviates
    from its Content Brief. Callers must route this to a `TypedFillFailure` or
    `StrategyChangeRequest`, not retry-and-hope."""

    def __init__(self, content_brief_id: str, violations: list[str]) -> None:
        self.content_brief_id = content_brief_id
        self.violations = violations
        super().__init__(f"{content_brief_id}: {'; '.join(violations)}")


def enforce_content_brief_compliance(
    brief: ContentBrief,
    produced: SpecialistOutputDeclaration,
) -> None:
    """Raise `SpecialistComplianceError` if `produced` deviates from `brief`.

    Covering *fewer* objectives/moves than approved is a fill failure (the
    specialist's problem to report via `TypedFillFailure`), not checked here.
    What is checked: methodology substitution, and objectives/moves outside
    what was ever approved -- both are silent scope/plan changes.
    """
    violations: list[str] = []
    if produced.methodology != brief.methodology:
        violations.append(
            f"methodology changed from {brief.methodology!r} to {produced.methodology!r}",
        )
    extra_objectives = set(produced.objectives_covered) - set(brief.objectives)
    if extra_objectives:
        violations.append(f"objectives outside the approved brief: {sorted(extra_objectives)}")
    if brief.learning_moves:
        extra_moves = set(produced.learning_moves_used) - set(brief.learning_moves)
        if extra_moves:
            violations.append(f"learning moves outside the approved brief: {sorted(extra_moves)}")
    if violations:
        raise SpecialistComplianceError(brief.content_brief_id, violations)
