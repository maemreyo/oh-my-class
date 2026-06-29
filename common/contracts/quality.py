from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QualityFailureClass(StrEnum):
    SCHEMA_INVALID = "schema_invalid"
    PLACEHOLDER_CONTENT = "placeholder_content"
    ANSWER_KEY_LEAKAGE = "answer_key_leakage"
    PII_LEAKAGE = "pii_leakage"
    EXTERNAL_ASSET = "external_asset"
    MISSING_DOCTYPE = "missing_doctype"
    MISSING_ACCESSIBILITY = "missing_accessibility"
    UNSUPPORTED_COMPONENT = "unsupported_component"
    FACTUAL_UNCERTAINTY = "factual_uncertainty"
    PEDAGOGICAL_MISMATCH = "pedagogical_mismatch"
    EXPORT_NOT_READY = "export_not_ready"


class HealingStrategy(StrEnum):
    SCHEMA_REPAIR = "schema_repair"
    ANSWER_KEY_REPAIR = "answer_key_repair"
    PII_REMOVAL = "pii_removal"
    PRESENTATION_REPAIR = "presentation_repair"
    ACCESSIBILITY_REPAIR = "accessibility_repair"
    REGENERATE_ARTIFACT = "regenerate_artifact"
    RESEARCH_ENRICHMENT = "research_enrichment"
    REPLAN_BLUEPRINT = "replan_blueprint"
    ESCALATE = "escalate"


class QualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_class: QualityFailureClass
    location: str
    message: str
    hard_block: bool = True


class ArtifactQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_type: str
    passed: bool
    issues: list[QualityIssue] = Field(default_factory=list)


class HealingDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_class: QualityFailureClass
    strategy: HealingStrategy
    max_attempts: int


class ExportReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    passed: bool
    approved_snapshot_ids: list[str] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
