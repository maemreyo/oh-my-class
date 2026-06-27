from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

PipelineMode = Literal["generate_pack", "diagnose_then_generate"]
ArtifactType = Literal["lesson", "worksheet", "quiz", "drill", "recap", "infographic"]
ExportFormat = Literal["html", "gift", "h5p", "qti", "google_forms"]
ResearchPolicy = Literal["basic", "standard", "rigorous"]
ContractActor = Literal["system", "teacher", "admin"]
ContractSource = Literal["code_defaults", "policy", "env", "request", "teacher", "admin"]


class ContractRevisionMeta(BaseModel):
    revision: int = Field(ge=1)
    actor: ContractActor
    source: ContractSource
    reason: str = Field(min_length=1, max_length=200)
    effective_stage: str = Field(min_length=1, max_length=64)


class RunContract(BaseModel):
    contract_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)
    teacher_id: str = Field(min_length=1, max_length=64)
    mode: PipelineMode = "generate_pack"
    topic: str = Field(min_length=1, max_length=200)
    grade_band: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=80)
    locale: str = Field(min_length=2, max_length=16)
    instruction_language: str = Field(min_length=2, max_length=32)
    curriculum: str | None = Field(default=None, max_length=80)
    citation_locale: str = Field(min_length=2, max_length=16)
    artifact_types: list[ArtifactType] = Field(min_length=1)
    export_formats: list[ExportFormat] = Field(min_length=1)
    research_policy: ResearchPolicy = "standard"
    config_version: str = Field(min_length=1, max_length=64)
    config_hash: str = Field(min_length=64, max_length=64)
    student_evidence: JsonObject | None = None
    revision_meta: ContractRevisionMeta


class ContractRevision(BaseModel):
    contract_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)
    contract: RunContract
    revision_meta: ContractRevisionMeta
