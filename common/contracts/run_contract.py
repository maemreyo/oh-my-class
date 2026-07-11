from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from common.contracts.education_policy import (
    EDUCATION_POLICY_VERSION,
    SubjectKey,
    CurriculumFrameworkValue,
    InstructionLanguageValue,
    SubjectKeyValue,
    TargetLanguageValue,
    normalize_language,
    normalize_subject,
)
from common.contracts.grade_band import GradeBand, grade_band_for_label

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

PipelineMode = Literal["generate_pack", "diagnose_then_generate", "plan_unit", "vocabulary_batch"]
ArtifactType = Literal[
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
    "flashcard_deck", "answer_key", "roadmap", "slide_deck", "reading_passage", "exit_ticket",
]
ExportFormat = Literal["html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "pptx"]
PublishTarget = Literal["google_forms"]
ResearchPolicy = Literal["basic", "standard", "rigorous"]
ContractActor = Literal["system", "teacher", "admin"]
ContractSource = Literal["code_defaults", "policy", "env", "request", "teacher", "admin"]
DecompositionIntentSource = Literal["teacher", "system", "admin"]


class ContractRevisionMeta(BaseModel):
    revision: int = Field(ge=1)
    actor: ContractActor
    source: ContractSource
    reason: str = Field(min_length=1, max_length=200)
    effective_stage: str = Field(min_length=1, max_length=64)


class DecompositionIntent(BaseModel):
    schema_version: Literal["decomposition_intent.v1"] = "decomposition_intent.v1"
    target_sessions: int = Field(ge=1, le=20)
    session_length_minutes: int = Field(ge=10, le=90)
    source: DecompositionIntentSource
    rationale: str = Field(min_length=1, max_length=500)


class RunContract(BaseModel):
    contract_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)
    teacher_id: str = Field(min_length=1, max_length=64)
    mode: PipelineMode = "generate_pack"
    topic: str = Field(min_length=1, max_length=200)
    education_policy_version: Literal["education_policy.v1"] = EDUCATION_POLICY_VERSION
    grade_band: Literal["k_2", "grades_3_5", "grades_6_8", "grades_9_12"]
    subject: SubjectKeyValue
    locale: str = Field(min_length=2, max_length=16)
    target_language: TargetLanguageValue = "en"
    instruction_language: InstructionLanguageValue
    curriculum: str | None = Field(default=None, max_length=80)
    curriculum_framework: CurriculumFrameworkValue = "general"
    citation_locale: str = Field(min_length=2, max_length=16)
    artifact_types: list[ArtifactType] = Field(min_length=1)
    export_formats: list[ExportFormat] = Field(min_length=1)
    publish_targets: list[PublishTarget] = Field(default_factory=list)
    research_policy: ResearchPolicy = "standard"
    config_version: str = Field(min_length=1, max_length=64)
    config_hash: str = Field(min_length=64, max_length=64)
    student_evidence: JsonObject | None = None
    decomposition_intent: DecompositionIntent | None = None
    revision_meta: ContractRevisionMeta

    @field_validator("grade_band", mode="before")
    @classmethod
    def _normalize_grade_band(cls, value: GradeBand | str) -> GradeBand | str:
        if isinstance(value, GradeBand):
            return value
        return grade_band_for_label(value) or value

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


class ContractRevision(BaseModel):
    contract_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)
    contract: RunContract
    revision_meta: ContractRevisionMeta
