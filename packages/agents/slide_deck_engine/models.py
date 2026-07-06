from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.run_contract import JsonObject
from common.contracts.slide_deck import SlideDeckData


class SlideDeckEngineRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1, max_length=64)
    lesson_blueprint: JsonObject
    research_brief: JsonObject
    dependency_artifacts: list[JsonObject] = Field(default_factory=list)
    teacher_constraints: JsonObject = Field(default_factory=dict)
    revision_feedback: str = ""


type SlideDeckValidationCode = Literal[
    "density_budget_ok",
    "density_budget_exceeded",
    "invalid_layout",
    "invalid_block",
    "invalid_interaction",
    "registry_membership_ok",
    "accessibility_ok",
    "missing_alt_text",
    "unsupported_media",
    "page_count_ok",
    "page_count_too_short",
    "page_count_exceeded",
    "pacing_ok",
    "pacing_mismatch",
    "source_refs_ok",
    "missing_source_refs",
    "surfaces_ready",
    "surfaces_incomplete",
    "teacher_only_separation_ok",
    "teacher_only_leak_risk",
    "objective_coverage_ok",
    "objective_coverage_gap",
    "html_exports_ready",
    "html_exports_incomplete",
]
type SlideDeckHealingScope = Literal["none", "block", "slide", "plan", "deck"]
type SlideDeckHealingStrategy = Literal["none", "retry", "rewrite", "reroute", "replan", "escalate"]
type SlideDeckHealingOutcome = Literal["not_needed", "planned", "repaired", "escalated"]
type SlideDeckFeedbackScope = Literal["none", "deck", "slide", "block", "interaction"]


class SlideDeckFeedbackTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: SlideDeckFeedbackScope = "none"
    reason: str = Field(default="", max_length=500)
    deck_id: str = Field(default="", max_length=80)
    slide_id: str = Field(default="", max_length=80)
    block_id: str = Field(default="", max_length=80)
    interaction_id: str = Field(default="", max_length=80)
    replacement_text: str = Field(default="", max_length=1000)
    theme: str = Field(default="", max_length=80)


class SlideDeckScopedRepairReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_scope: SlideDeckFeedbackScope = "none"
    applied_scope: SlideDeckHealingScope = "none"
    target_id: str = ""
    reason: str = ""
    escalated: bool = False
    escalation_reason: str = ""
    preserved_slide_ids: list[str] = Field(default_factory=list)
    preserved_non_slide_artifacts: bool = True


class SlideDeckValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: str = Field(min_length=1, max_length=80)
    passed: bool
    code: SlideDeckValidationCode
    message: str = Field(min_length=1, max_length=300)
    scope: SlideDeckHealingScope = "deck"


class SlideDeckHealingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempted: bool = False
    failure_code: SlideDeckValidationCode | None = None
    scope: SlideDeckHealingScope = "none"
    strategy: SlideDeckHealingStrategy = "none"
    outcome: SlideDeckHealingOutcome = "not_needed"
    final_status: Literal["passed", "failed", "not_applicable"] = "not_applicable"
    message: str = "No healing required."


class SlideDeckScorecard(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_score: float = Field(ge=0.0, le=1.0)
    density_score: float = Field(ge=0.0, le=1.0)
    accessibility_score: float = Field(ge=0.0, le=1.0)
    surface_score: float = Field(ge=0.0, le=1.0)
    objective_coverage_score: float = Field(ge=0.0, le=1.0)
    pacing_fit_score: float = Field(ge=0.0, le=1.0)
    visual_variety_score: float = Field(ge=0.0, le=1.0)
    interaction_appropriateness_score: float = Field(ge=0.0, le=1.0)
    teacher_only_separation_score: float = Field(ge=0.0, le=1.0)
    offline_readiness_score: float = Field(ge=0.0, le=1.0)
    source_reference_score: float = Field(ge=0.0, le=1.0)


class SlideDeckTraceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1, max_length=64)
    phases: list[str] = Field(default_factory=list)
    llm_calls: int = Field(ge=0)
    internal_only: bool = True
    plan_artifact: JsonObject
    data_artifact: JsonObject
    validation_artifact: JsonObject
    healing_artifact: JsonObject
    scorecard_artifact: JsonObject
    source_ref_map: JsonObject
    model_cost_metadata: JsonObject
    export_readiness_manifest: JsonObject
    scoped_regeneration_artifact: JsonObject = Field(default_factory=dict)


class SlideDeckEngineResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    deck: SlideDeckData
    validation_reports: list[SlideDeckValidationReport]
    healing_reports: list[SlideDeckHealingReport]
    scorecard: SlideDeckScorecard
    trace: SlideDeckTraceMetadata


class AssembledSlideDeckInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    topic: str
    grade_level: str
    locale: str
    theme: str
    source: JsonObject


class PedagogicalPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    learning_goal: str
    check_prompt: str


class SlideArchitecturePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    slide_titles: list[str] = Field(min_length=1)
    layouts: list[str] = Field(min_length=1)
