from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.contracts.education_policy import (
    EDUCATION_POLICY_VERSION,
    InstructionLanguageValue,
    SubjectKey,
    TargetLanguageValue,
    normalize_language,
    normalize_subject,
)
from common.contracts.run_contract import ArtifactType, ExportFormat, ResearchPolicy

DEFAULT_ARTIFACT_TYPES: list[ArtifactType] = [
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "slide_deck",
]


class TeachingBrief(BaseModel):
    """Teacher-authored intent that is autosaved before creating a run."""

    model_config = ConfigDict(frozen=True)

    raw_request: str = Field(min_length=1, max_length=4_000)
    topic: str = Field(min_length=1, max_length=200)
    grade: int = Field(ge=1, le=12)
    education_policy_version: Literal["education_policy.v1"] = EDUCATION_POLICY_VERSION
    subject: SubjectKey
    target_language: TargetLanguageValue = "en"
    instruction_language: InstructionLanguageValue = "en"
    curriculum: str | None = Field(default=None, max_length=80)
    class_context: str = Field(default="", max_length=1_000)
    artifact_types: list[ArtifactType] = Field(default_factory=lambda: list(DEFAULT_ARTIFACT_TYPES))
    export_formats: list[ExportFormat] = Field(default_factory=lambda: ["html"])
    methodology: str | None = Field(default=None, max_length=80)
    research_policy: ResearchPolicy = "standard"
    must_include: str = Field(default="", max_length=1_000)
    avoid: str = Field(default="", max_length=1_000)
    always_review: bool = False

    @field_validator("subject", mode="before")
    @classmethod
    def _normalize_subject(cls, value: SubjectKey | str) -> SubjectKey | str:
        if isinstance(value, SubjectKey):
            return value
        return normalize_subject(value) or value

    @field_validator("target_language", "instruction_language", mode="before")
    @classmethod
    def _normalize_language(cls, value: str) -> InstructionLanguageValue | str:
        return normalize_language(value) or value


MaterialityReason = Literal[
    "always_review",
    "rigorous_research",
    "custom_artifact_scope",
    "non_html_export",
    "methodology_preference",
]


def materiality_reasons(brief: TeachingBrief) -> list[MaterialityReason]:
    """Return the teacher-visible reasons that require Planning Review."""
    reasons: list[MaterialityReason] = []
    if brief.always_review:
        reasons.append("always_review")
    if brief.research_policy == "rigorous":
        reasons.append("rigorous_research")
    if brief.artifact_types != DEFAULT_ARTIFACT_TYPES:
        reasons.append("custom_artifact_scope")
    if brief.export_formats != ["html"]:
        reasons.append("non_html_export")
    if brief.methodology is not None:
        reasons.append("methodology_preference")
    return reasons
