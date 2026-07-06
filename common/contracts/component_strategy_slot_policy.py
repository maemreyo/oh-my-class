from __future__ import annotations

from common.contracts.component_strategy import ComponentStrategyRequest, StrategySlot, StrategySlotBudget
from common.contracts.component_strategy_slot_contracts import (
    ArtifactScopeRecommendation,
    StrategyAssessmentIntent,
    StrategyDeliveryContext,
    StrategyDeliveryMode,
    StrategyFeedbackLevel,
    StrategyScoringIntent,
    StrategyScoringMode,
)


def delivery_context_for(request: ComponentStrategyRequest) -> StrategyDeliveryContext:
    if isinstance(request.delivery, StrategyDeliveryContext):
        return request.delivery
    return StrategyDeliveryContext.model_validate(request.delivery)


def scoring_intent_for(request: ComponentStrategyRequest) -> StrategyScoringIntent:
    intent = _assessment_intent_for(request)
    if intent in {StrategyAssessmentIntent.SUMMATIVE, StrategyAssessmentIntent.EXAM_PREP}:
        return StrategyScoringIntent(
            mode=StrategyScoringMode.AUTO_GRADABLE,
            assessment_intent=intent,
            partial_credit_allowed=True,
            rationale_required=True,
            feedback_level=StrategyFeedbackLevel.FULL_EXPLANATION,
        )
    if delivery_context_for(request).mode is StrategyDeliveryMode.HOMEWORK:
        return StrategyScoringIntent(mode=StrategyScoringMode.SELF_CHECK, assessment_intent=intent)
    return StrategyScoringIntent(assessment_intent=intent)


def slot_budget_for(request: ComponentStrategyRequest, *, min_minutes: int, max_minutes: int) -> StrategySlotBudget:
    teacher_load = "low" if delivery_context_for(request).mode is StrategyDeliveryMode.HOMEWORK else "medium"
    return StrategySlotBudget(
        ideal_time_minutes=max(1, min_minutes),
        max_time_minutes=max(1, max_minutes),
        ideal_item_count=1,
        max_item_count=3,
        teacher_load_level=teacher_load,
    )


def fill_requirements_for(learning_move_id: str) -> tuple[str, ...]:
    return (
        f"fill_policy:{learning_move_id}",
        "distractor_coverage_mapping_required",
        "teacher_only_rationale_required",
    )


def forbidden_fill_patterns() -> tuple[str, ...]:
    return ("answer_key_in_student_view", "uncited_high_risk_claim", "exact_distractor_text")


def teacher_load_multiplier(request: ComponentStrategyRequest) -> float:
    class_size = request.delivery_context.get("class_size")
    prep_load = request.delivery_context.get("teacher_prep_load")
    if class_size == 48 or prep_load == "high":
        return 0.85
    return 1.0


def artifact_scope_recommendations_for(request: ComponentStrategyRequest) -> tuple[ArtifactScopeRecommendation, ...]:
    if "exam_prep" not in request.assessment_intent:
        return ()
    if "quiz" in request.artifact_types:
        return ()
    return (ArtifactScopeRecommendation(
        artifact_type="quiz",
        recommendation="Consider adding a quiz for exam-prep assessment while keeping requested artifacts unchanged.",
    ),)


def scaffold_slot_for(request: ComponentStrategyRequest, parent: StrategySlot) -> StrategySlot:
    return parent.model_copy(update={
        "slot_id": f"{request.run_id}/scaffold/slot-0",
        "sequence_id": "seq-0",
        "phase": "activate",
        "learning_move_id": "prerequisite_scaffold",
        "component_type": "active_recall_prompt",
        "component_binding_id": "scaffold-prerequisite@1.0.0",
        "fill_requirements": ("activate_prerequisite_knowledge",),
        "budget": StrategySlotBudget(
            ideal_time_minutes=5,
            max_time_minutes=8,
            ideal_item_count=1,
            max_item_count=2,
            teacher_load_level="low",
        ),
        "parent_slot_id": None,
    })


def _assessment_intent_for(request: ComponentStrategyRequest) -> StrategyAssessmentIntent:
    for value in request.assessment_intent:
        if value in StrategyAssessmentIntent:
            return StrategyAssessmentIntent(value)
    if "quiz" in request.artifact_types:
        return StrategyAssessmentIntent.FORMATIVE
    return StrategyAssessmentIntent.FORMATIVE
