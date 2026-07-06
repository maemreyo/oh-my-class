from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class KnowledgeManifest(KnowledgeModel):
    knowledge_db_version: str = Field(min_length=1)
    manifest_checksum: str = Field(min_length=1)
    source_checksum: str = Field(min_length=1)
    sqlite_checksum: str = Field(min_length=1)
    renderer_capability_checksum: str = Field(min_length=1)
    exporter_capability_checksum: str = Field(min_length=1)
    compatible_strategy_schema_versions: tuple[str, ...] = Field(min_length=1)
    compatible_selector_versions: tuple[str, ...] = Field(min_length=1)
    supported_locales: tuple[str, ...] = Field(min_length=1)


class EvidenceSource(KnowledgeModel):
    evidence_id: str = Field(min_length=1)
    citation: str = Field(min_length=1)


class LearningMoveEntry(KnowledgeModel):
    move_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    lifecycle: Literal["production", "draft", "deprecated"]
    production_selectable: bool
    labels: dict[str, str]
    subject_tags: tuple[str, ...] = Field(min_length=1)
    grade_bands: tuple[str, ...] = Field(min_length=1)
    bloom_levels: tuple[str, ...] = Field(min_length=1)
    moet_levels: tuple[str, ...] = Field(min_length=1)
    gagne_events: tuple[str, ...] = Field(min_length=1)
    udl_tags: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    fill_validation_policy: str = Field(min_length=1)


class ComponentBindingEntry(KnowledgeModel):
    binding_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    lifecycle: Literal["production", "draft", "deprecated"]
    production_selectable: bool
    component_type: str = Field(min_length=1)
    learning_move_id: str = Field(min_length=1)
    strategy_family_ids: tuple[str, ...] = Field(min_length=1)
    artifact_types: tuple[str, ...] = Field(min_length=1)
    subject_tags: tuple[str, ...] = Field(min_length=1)
    grade_bands: tuple[str, ...] = Field(min_length=1)
    bloom_levels: tuple[str, ...] = Field(min_length=1)
    moet_levels: tuple[str, ...] = Field(min_length=1)
    gagne_events: tuple[str, ...] = Field(min_length=1)
    udl_tags: tuple[str, ...] = Field(min_length=1)
    duration_min_minutes: int = Field(ge=1, le=180)
    duration_max_minutes: int = Field(ge=1, le=180)
    compliance_risk: Literal["low", "medium", "high"]
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    fallback_policy_id: str = Field(min_length=1)
    labels: dict[str, str]
    rationale_template: dict[str, str]


class StrategyFamilyEntry(KnowledgeModel):
    family_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    lifecycle: Literal["production", "draft", "deprecated"]
    production_selectable: bool
    labels: dict[str, str]
    subject_tags: tuple[str, ...] = Field(min_length=1)
    required_learning_move_ids: tuple[str, ...] = Field(min_length=1)
    scoring_profile_id: str = Field(min_length=1)


class ScoringProfileEntry(KnowledgeModel):
    scoring_profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    weights: dict[str, float]
    fallback_only: bool = False


class FallbackPolicyEntry(KnowledgeModel):
    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    lifecycle: Literal["production", "draft", "deprecated"]
    fallback_policy: Literal["required", "terminal_safe", "no_fallback_allowed"]
    from_component_type: str = Field(min_length=1)
    to_component_type: str = Field(min_length=1)
    preserved_affordances: tuple[str, ...] = Field(default_factory=tuple)
    lost_affordances: tuple[str, ...] = Field(default_factory=tuple)
    fallback_quality: float = Field(ge=0, le=1)
    reason_code: str = Field(min_length=1)
    teacher_message: str = Field(min_length=1)
    severity: Literal["info", "warning", "block"]
    teacher_options: tuple[str, ...] = Field(default_factory=tuple)


class ContraindicationEntry(KnowledgeModel):
    rule_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    lifecycle: Literal["production", "draft", "deprecated"]
    priority: int | None = Field(default=None, ge=0)
    component_type: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    override_allowed: bool = False


class RationaleTemplateEntry(KnowledgeModel):
    template_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    labels: dict[str, str]


class ComponentKnowledgeSource(KnowledgeModel):
    manifest: KnowledgeManifest
    evidence_sources: tuple[EvidenceSource, ...] = Field(min_length=1)
    learning_moves: tuple[LearningMoveEntry, ...] = Field(min_length=1)
    component_bindings: tuple[ComponentBindingEntry, ...] = Field(min_length=1)
    strategy_families: tuple[StrategyFamilyEntry, ...] = Field(min_length=1)
    scoring_profiles: tuple[ScoringProfileEntry, ...] = Field(min_length=1)
    fallback_policies: tuple[FallbackPolicyEntry, ...] = Field(min_length=1)
    contraindications: tuple[ContraindicationEntry, ...] = Field(default_factory=tuple)
    rationale_templates: tuple[RationaleTemplateEntry, ...] = Field(default_factory=tuple)


class KnowledgeValidationReport(KnowledgeModel):
    manifest: KnowledgeManifest
    production_families: tuple[StrategyFamilyEntry, ...]
    production_bindings: tuple[ComponentBindingEntry, ...]


class CapabilityComponentEntry(KnowledgeModel):
    component_type: str = Field(min_length=1)
    supported_artifact_types: tuple[str, ...] = Field(default_factory=tuple)
    required_fields: tuple[str, ...] = Field(default_factory=tuple)
    template: str | None = None
    cognitive_load: Literal["low", "medium", "high"]
    print_risk: Literal["low", "medium", "high"]
    item_limit: int | None = Field(default=None, ge=1)
    accessibility_requirements: tuple[str, ...] = Field(default_factory=tuple)
    known_limitations: tuple[str, ...] = Field(default_factory=tuple)


class RendererCapabilityManifest(KnowledgeModel):
    manifest_version: str = Field(min_length=1)
    generated_from: str = Field(min_length=1)
    components: tuple[CapabilityComponentEntry, ...] = Field(min_length=1)


class ExporterCapabilityEntry(KnowledgeModel):
    export_format: str = Field(min_length=1)
    supported_artifact_types: tuple[str, ...] = Field(default_factory=tuple)
    known_limitations: tuple[str, ...] = Field(default_factory=tuple)


class ExporterCapabilityManifest(KnowledgeModel):
    manifest_version: str = Field(min_length=1)
    generated_from: str = Field(min_length=1)
    exporters: tuple[ExporterCapabilityEntry, ...] = Field(min_length=1)


class BuiltKnowledgeManifest(KnowledgeModel):
    knowledge_db_version: str
    source_checksum: str
    sqlite_checksum: str
    output_path: str


class KnowledgeQuery(KnowledgeModel):
    artifact_type: str | None = None
    subject_tag: str | None = None
    grade_band: str | None = None
    bloom_level: str | None = None
    moet_level: str | None = None
    gagne_event: str | None = None
    udl_tag: str | None = None
    max_duration_minutes: int | None = None
    compliance_risk: Literal["low", "medium", "high"] | None = None
    strategy_family_id: str | None = None


class KnowledgeBindingResult(KnowledgeModel):
    binding_id: str
    component_type: str
    learning_move_id: str
    strategy_family_ids: tuple[str, ...]
    artifact_types: tuple[str, ...]
    duration_max_minutes: int
    compliance_risk: str
