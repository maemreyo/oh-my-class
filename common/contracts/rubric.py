"""Canonical rubric registry contracts for adaptive judging.

Defines the single-source-of-truth Pydantic models for G-Eval rubrics:
- RubricLevel: a scoring level within a criterion
- RubricCriterion: a named criterion with weight and scoring levels
- Rubric: immutable collection of criteria; weights validated to sum to 1.0 ± 0.001
- RubricRegistry: versioned registry with dedup for adaptive judge lookup

These contracts sit in common/contracts (INVARIANT-10) so that both the
Python quality gates and the TypeScript renderer reference the same schema.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Iterator


class RubricLevel(BaseModel):
    """A single scoring level within a rubric criterion."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(
        ..., description="Numerical score for this level"
    )
    description: str = Field(
        ..., min_length=1, description="Human-readable description"
    )


class RubricCriterion(BaseModel):
    """A named evaluation criterion with a non-negative weight (0–1).

    Mirrors the TypeScript ``RubricCriterion`` interface in
    ``packages/renderer/src/contracts/questions/base.ts``.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        ..., min_length=1, description="Unique criterion name within a rubric"
    )
    weight: float = Field(
        ...,
        ge=0,
        le=1,
        description="Non-negative weight; must sum to 1.0 across rubric",
    )
    levels: list[RubricLevel] = Field(default_factory=list)
    descriptors: dict[str, str] | None = Field(
        default=None,
        description="Optional quality descriptors by level name",
    )


class Rubric(BaseModel):
    """An immutable, versioned rubric for G-Eval scoring.

    Invariants:
    - ``version_id`` is required and immutable (frozen model).
    - All criterion ``weight`` values are non-negative.
    - Criterion weights must sum to 1.0 ± 0.001.
    - Criterion names within a rubric must be unique.
    - The model is frozen (immutable) and hashable by ``version_id``.
    """

    model_config = ConfigDict(frozen=True)

    version_id: str = Field(
        ...,
        min_length=1,
        description="Immutable version identifier",
    )
    criteria: list[RubricCriterion] = Field(..., min_length=1)
    description: str = ""

    def __hash__(self) -> int:
        return hash(self.version_id)

    @model_validator(mode="after")
    def _validate_weights_sum(self) -> Rubric:
        total = sum(c.weight for c in self.criteria)
        if abs(total - 1.0) > 0.001:
            msg = (
                "Rubric weights must sum to 1.0 ± 0.001, "
                f"got {total:.6f}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_criterion_names_unique(self) -> Rubric:
        names = [c.name for c in self.criteria]
        if len(names) != len(set(names)):
            msg = "Rubric criterion names must be unique"
            raise ValueError(msg)
        return self


class RubricRegistry:
    """Versioned registry for canonical rubrics.

    Stores rubrics by ``version_id``. Duplicate registrations of the same
    ``version_id`` are rejected. Supports iteration, membership testing,
    and length queries for adaptive judge workflows.
    """

    def __init__(self) -> None:
        self._rubrics: dict[str, Rubric] = {}

    def register(self, rubric: Rubric) -> None:
        """Register a rubric.

        Raises ``TypeError`` if not a Rubric.
        Raises ``ValueError`` on duplicate version_id.
        """
        if not isinstance(rubric, Rubric):
            msg = (
                f"Expected Rubric, got {type(rubric).__name__}"
            )
            raise TypeError(msg)
        if rubric.version_id in self._rubrics:
            msg = (
                "Duplicate rubric version_id: "
                f"{rubric.version_id!r}"
            )
            raise ValueError(msg)
        self._rubrics[rubric.version_id] = rubric

    def get(self, version_id: str) -> Rubric | None:
        """Lookup a rubric by version_id. Returns ``None`` if not found."""
        return self._rubrics.get(version_id)

    def remove(self, version_id: str) -> None:
        """Remove a rubric by version_id. Raises ``KeyError`` if not found."""
        if version_id not in self._rubrics:
            raise KeyError(version_id)
        del self._rubrics[version_id]

    def list_versions(self) -> list[str]:
        """Return sorted list of all registered version IDs."""
        return sorted(self._rubrics.keys())

    def __contains__(self, version_id: str) -> bool:
        return version_id in self._rubrics

    def __len__(self) -> int:
        return len(self._rubrics)

    def __iter__(self) -> Iterator[Rubric]:
        return iter(self._rubrics.values())
