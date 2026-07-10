"""Subject Capability Pack contract (ADR-053, #447-450).

Governed capability evidence for one subject across the four canonical
Grade Bands (common.contracts.grade_band.GradeBand): which artifact
families are covered, which curriculum standards (MOET/CCSS/NGSS) are
claimed per band, and which misconceptions each band's content must guard
against. Mirrors the fail-closed validation style of
common.contracts.teaching_pack_capabilities -- a pack that claims a
standard or misconception for a band without content backing it is a
schema error, not a soft warning.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from common.contracts.grade_band import GradeBand

CurriculumFramework = Literal["MOET_2018", "CCSS", "NGSS"]


class CurriculumStandard(BaseModel):
    """One traceable standard claim (e.g. CCSS.MATH.CONTENT.5.NF.A.1)."""

    model_config = ConfigDict(frozen=True)

    framework: CurriculumFramework
    code: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    description_vi: str = Field(min_length=1)


class MisconceptionEntry(BaseModel):
    """One documented, guarded-against misconception for a Grade Band."""

    model_config = ConfigDict(frozen=True)

    misconception_id: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    description_vi: str = Field(min_length=1)
    guard_strategy: str = Field(min_length=1, description="How generated content avoids reinforcing this")


class GradeBandCoverage(BaseModel):
    """One Grade Band's certified coverage for a subject."""

    model_config = ConfigDict(frozen=True)

    grade_band: GradeBand
    artifact_families: tuple[str, ...] = Field(min_length=1)
    standards: tuple[CurriculumStandard, ...] = Field(min_length=1)
    misconceptions: tuple[MisconceptionEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_both_frameworks_or_ngss(self) -> GradeBandCoverage:
        frameworks = {standard.framework for standard in self.standards}
        if "MOET_2018" not in frameworks:
            raise PydanticCustomError(
                "moet_standard_required",
                "every grade band must claim at least one MOET_2018 standard for bilingual traceability",
            )
        return self


class SubjectCapabilityPack(BaseModel):
    """One versioned, governed capability declaration for a subject."""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    deterministic_solver: str | None = Field(
        default=None,
        description="Dotted path to the solver module backing answer verification, if any",
    )
    grade_bands: tuple[GradeBandCoverage, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_every_canonical_grade_band(self) -> SubjectCapabilityPack:
        declared = {coverage.grade_band for coverage in self.grade_bands}
        missing = set(GradeBand) - declared
        if missing:
            raise PydanticCustomError(
                "missing_grade_bands",
                "subject capability pack is missing grade bands: {missing}",
                {"missing": sorted(band.value for band in missing)},
            )
        duplicates = _duplicates(coverage.grade_band for coverage in self.grade_bands)
        if duplicates:
            raise PydanticCustomError(
                "duplicate_grade_bands",
                "subject capability pack declares a grade band more than once: {duplicates}",
                {"duplicates": sorted(band.value for band in duplicates)},
            )
        return self

    def coverage_for(self, grade_band: GradeBand) -> GradeBandCoverage:
        for coverage in self.grade_bands:
            if coverage.grade_band == grade_band:
                return coverage
        raise KeyError(f"no coverage declared for grade band {grade_band!r}")


def load_subject_capability_pack(path: Path) -> SubjectCapabilityPack:
    return SubjectCapabilityPack.model_validate_json(path.read_text())


def _duplicates(values: Iterable[GradeBand]) -> set[GradeBand]:
    counts: dict[GradeBand, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return {value for value, count in counts.items() if count > 1}
