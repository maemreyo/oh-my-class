from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from common.contracts.component_strategy_enums import (
    ComponentStrategyMode,
    ComponentStrategyStatus,
    ComplianceSafety,
    ExportProjectionState,
    FeedbackEventType,
    FeedbackSource,
    PrerequisiteRisk,
    ResearchRiskLevel,
    RevisionActor,
    SourceConfidence,
    StrategyBlockingIssueCode,
    StrategyRevisionMateriality,
    StrategyWarningCode,
)
from common.contracts.component_strategy_slot_contracts import (
    ArtifactScopeRecommendation,
    MisconceptionTarget,
    StrategyDeliveryContext,
    StrategyLoadLevel,
    StrategyScoringIntent,
    StrategySlotExpansionPolicy,
)


class StrategyModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ObjectiveRef(StrategyModel):
    objective_id: str = Field(min_length=1, max_length=80)
    objective_revision: str = Field(min_length=1, max_length=80)
    importance: Literal["core", "supporting", "extension"] = "core"
    assessable: bool = True


class ObjectiveCoverage(StrategyModel):
    objective_ref: ObjectiveRef
    coverage_state: Literal["covered", "deferred", "uncovered"]
    slot_ids: tuple[str, ...] = Field(default_factory=tuple)
    note: str = Field(min_length=1, max_length=240)


class ResearchSignals(StrategyModel):
    factual_risk: ResearchRiskLevel
    source_confidence: SourceConfidence
    prerequisite_risk: PrerequisiteRisk
    misconception_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_tags: tuple[str, ...] = Field(default_factory=tuple)


class TeacherPreferenceSignals(StrategyModel):
    feedback_events: tuple["StrategyFeedbackEvent", ...] = Field(default_factory=tuple)
    priority_objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    assessable_objective_ids: tuple[str, ...] = Field(default_factory=tuple)


class StrategyFeedbackEvent(StrategyModel):
    event_id: str = Field(min_length=1, max_length=80)
    event_type: FeedbackEventType
    source: FeedbackSource
    value: str = Field(min_length=1, max_length=120)
    rationale: str | None = Field(default=None, max_length=500)


class StrategySlotBudget(StrategyModel):
    ideal_time_minutes: int = Field(ge=1, le=180)
    max_time_minutes: int = Field(ge=1, le=180)
    ideal_item_count: int = Field(ge=1, le=100)
    max_item_count: int = Field(ge=1, le=100)
    teacher_load_level: Literal["low", "medium", "high"] = "medium"
    reading_level: str = Field(default="grade_level", min_length=1, max_length=80)
    cognitive_load: StrategyLoadLevel = StrategyLoadLevel.MEDIUM
    scaffold_level: StrategyLoadLevel = StrategyLoadLevel.LOW
    print_density: StrategyLoadLevel = StrategyLoadLevel.MEDIUM
    grading_load: StrategyLoadLevel = StrategyLoadLevel.LOW

    @model_validator(mode="after")
    def validate_budget_bounds(self) -> "StrategySlotBudget":
        if self.max_time_minutes < self.ideal_time_minutes:
            raise ValueError("max_time_minutes must be >= ideal_time_minutes")
        if self.max_item_count < self.ideal_item_count:
            raise ValueError("max_item_count must be >= ideal_item_count")
        return self


class StrategySlot(StrategyModel):
    slot_id: str = Field(min_length=1, max_length=160)
    sequence_id: str = Field(min_length=1, max_length=120)
    phase: str = Field(min_length=1, max_length=80)
    learning_move_id: str = Field(min_length=1, max_length=120)
    component_type: str = Field(min_length=1, max_length=120)
    component_binding_id: str = Field(min_length=1, max_length=160)
    objective_refs: tuple[ObjectiveRef, ...] = Field(min_length=1)
    target_artifacts: tuple[str, ...] = Field(min_length=1)
    required_affordances: tuple[str, ...] = Field(default_factory=tuple)
    fill_requirements: tuple[str, ...] = Field(default_factory=tuple)
    forbidden_fill_patterns: tuple[str, ...] = Field(default_factory=tuple)
    accessibility_intent: tuple[str, ...] = Field(default_factory=tuple)
    differentiation_intent: tuple[str, ...] = Field(default_factory=tuple)
    budget: StrategySlotBudget
    scoring_intent: StrategyScoringIntent = Field(default_factory=StrategyScoringIntent)
    teacher_action_intent: tuple[str, ...] = Field(default_factory=tuple)
    student_instruction_constraints: tuple[str, ...] = Field(default_factory=tuple)
    misconception_targets: tuple[MisconceptionTarget, ...] = Field(default_factory=tuple)
    expansion_policy: StrategySlotExpansionPolicy = Field(default_factory=StrategySlotExpansionPolicy)
    parent_slot_id: str | None = Field(default=None, max_length=160)


class ArtifactStrategyProjection(StrategyModel):
    artifact_type: str = Field(min_length=1, max_length=80)
    ordered_slot_ids: tuple[str, ...] = Field(min_length=1)
    notes_for_creator: tuple[str, ...] = Field(default_factory=tuple)


class ExportProjectionStatus(StrategyModel):
    export_format: str = Field(min_length=1, max_length=80)
    slot_id: str = Field(min_length=1, max_length=160)
    state: ExportProjectionState
    fallback_component_type: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


class FallbackMetadata(StrategyModel):
    fallback_graph_version: str = Field(min_length=1, max_length=80)
    original_component_type: str = Field(min_length=1, max_length=120)
    fallback_component_type: str = Field(min_length=1, max_length=120)
    reason_code: str = Field(min_length=1, max_length=120)
    teacher_visible_note: str = Field(min_length=1, max_length=500)
    severity: Literal["info", "warning", "block"] = "warning"
    fallback_quality: float = Field(default=1.0, ge=0, le=1)
    preserved_affordances: tuple[str, ...] = Field(default_factory=tuple)
    lost_affordances: tuple[str, ...] = Field(default_factory=tuple)


class StrategyQualityScore(StrategyModel):
    overall: float = Field(ge=0, le=1)
    objective_alignment: float = Field(ge=0, le=1)
    evidence_signal_coverage: float = Field(ge=0, le=1)
    component_diversity: float = Field(ge=0, le=1)
    compliance_safety: ComplianceSafety
    audit_ledger: dict[str, float | str | bool] = Field(default_factory=dict)


class StrategyBlockingIssue(StrategyModel):
    code: StrategyBlockingIssueCode
    message: str = Field(min_length=1, max_length=500)
    affected_objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    teacher_options: tuple[str, ...] = Field(default_factory=tuple)


class StrategyWarning(StrategyModel):
    code: StrategyWarningCode
    message: str = Field(min_length=1, max_length=500)
    slot_ids: tuple[str, ...] = Field(default_factory=tuple)


class StrategyVariant(StrategyModel):
    variant_id: str = Field(min_length=1, max_length=80)
    strategy_family_id: str = Field(min_length=1, max_length=120)
    display_label: str = Field(min_length=1, max_length=120)
    learning_sequence: tuple[StrategySlot, ...] = Field(min_length=1)
    artifact_strategies: tuple[ArtifactStrategyProjection, ...] = Field(min_length=1)
    export_projection_status: tuple[ExportProjectionStatus, ...] = Field(default_factory=tuple)
    quality_score: StrategyQualityScore
    fallback_metadata: FallbackMetadata | None = None
    rejection_reasons: tuple[str, ...] = Field(default_factory=tuple)


class StrategyRevision(StrategyModel):
    revision_id: str = Field(min_length=1, max_length=80)
    parent_revision_id: str | None = Field(default=None, max_length=80)
    actor: RevisionActor
    reason: str = Field(min_length=1, max_length=500)
    materiality: StrategyRevisionMateriality = StrategyRevisionMateriality.NONE
    teacher_reapproval_required: bool


class ComponentStrategyPlan(StrategyModel):
    strategy_id: str = Field(min_length=1, max_length=120)
    strategy_schema_version: str = Field(min_length=1, max_length=80)
    knowledge_db_version: str = Field(min_length=1, max_length=80)
    selector_version: str = Field(min_length=1, max_length=80)
    scoring_profile_id: str = Field(min_length=1, max_length=120)
    blueprint_revision_id: str = Field(min_length=1, max_length=80)
    objective_refs: tuple[ObjectiveRef, ...] = Field(min_length=1)
    recommended: StrategyVariant
    variants: tuple[StrategyVariant, ...] = Field(default_factory=tuple)
    rationale_text: str = Field(min_length=1, max_length=1200)
    rationale_facts: tuple[str, ...] = Field(default_factory=tuple)
    audit_score_ledger: dict[str, float | str | bool] = Field(default_factory=dict)
    objective_coverage: tuple[ObjectiveCoverage, ...] = Field(default_factory=tuple)
    delivery_context: StrategyDeliveryContext = Field(default_factory=StrategyDeliveryContext)
    artifact_scope_recommendations: tuple[ArtifactScopeRecommendation, ...] = Field(default_factory=tuple)
    revision: StrategyRevision | None = None


class ComponentStrategyRequest(StrategyModel):
    mode: ComponentStrategyMode
    run_id: str = Field(min_length=1, max_length=80)
    teacher_id_hash: str = Field(min_length=1, max_length=128)
    locale: str = Field(min_length=2, max_length=16)
    subject: str = Field(min_length=1, max_length=80)
    grade_level: str = Field(min_length=1, max_length=80)
    duration_minutes: int = Field(ge=10, le=180)
    artifact_types: tuple[str, ...] = Field(min_length=1)
    export_formats: tuple[str, ...] = Field(min_length=1)
    objective_refs: tuple[ObjectiveRef, ...] = Field(min_length=1)
    delivery_context: dict[str, str | int | bool] = Field(default_factory=dict)
    delivery: StrategyDeliveryContext = Field(default_factory=StrategyDeliveryContext)
    assessment_intent: tuple[str, ...] = Field(default_factory=tuple)
    research_signals: ResearchSignals | None = None
    teacher_preferences: TeacherPreferenceSignals | None = None

    @model_validator(mode="after")
    def reject_individual_student_context(self) -> "ComponentStrategyRequest":
        from common.contracts.component_strategy_privacy import contains_forbidden_delivery_context

        forbidden = contains_forbidden_delivery_context(set(self.delivery_context))
        if forbidden is not None:
            raise ValueError(f"selector request cannot include individual-student field {forbidden}")
        return self


class ComponentStrategyResult(StrategyModel):
    status: ComponentStrategyStatus
    plan: ComponentStrategyPlan | None = None
    research_questions: tuple[str, ...] = Field(default_factory=tuple)
    hypotheses: tuple[str, ...] = Field(default_factory=tuple)
    blocking_issues: tuple[StrategyBlockingIssue | StrategyBlockingIssueCode, ...] = Field(
        default_factory=tuple
    )
    warnings: tuple[StrategyWarning, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_status_payload(self) -> "ComponentStrategyResult":
        if self.status is ComponentStrategyStatus.BLOCKED and self.plan is not None:
            raise ValueError("blocked results cannot carry a plan")
        if (
            self.status is not ComponentStrategyStatus.BLOCKED
            and self.plan is None
            and not self.research_questions
            and not self.hypotheses
        ):
            raise ValueError("planned results must carry a plan")
        return self
