from __future__ import annotations

from common.contracts.component_strategy import (
    ComponentStrategyRequest,
    ComponentStrategyResult,
    ObjectiveRef,
    ResearchSignals,
    StrategyFeedbackEvent,
    TeacherPreferenceSignals,
)
from common.contracts.component_strategy_selector import plan_component_strategy


def _objective(
    objective_id: str = "LO-1",
    *,
    importance: str = "core",
    assessable: bool = True,
) -> ObjectiveRef:
    return ObjectiveRef(
        objective_id=objective_id,
        objective_revision="rev-1",
        importance=importance,
        assessable=assessable,
    )


def _research() -> ResearchSignals:
    return ResearchSignals(
        factual_risk="low",
        source_confidence="high",
        prerequisite_risk="met",
        evidence_tags=("retrieval_practice", "contrastive_examples"),
    )


def _request(
    subject: str,
    artifact_types: tuple[str, ...],
    assessment_intent: tuple[str, ...] = (),
    teacher_preferences: TeacherPreferenceSignals | None = None,
    objective_refs: tuple[ObjectiveRef, ...] | None = None,
) -> ComponentStrategyRequest:
    return ComponentStrategyRequest(
        mode="final",
        run_id="run-1",
        teacher_id_hash="teacher-hash",
        locale="vi",
        subject=subject,
        grade_level="Grade 5",
        duration_minutes=45,
        artifact_types=artifact_types,
        export_formats=("html",),
        objective_refs=objective_refs or (_objective(),),
        assessment_intent=assessment_intent,
        research_signals=_research(),
        teacher_preferences=teacher_preferences,
    )


def test_provisional_mode_emits_hypotheses_without_final_snapshot() -> None:
    request = _request(subject="language", artifact_types=("lesson",)).model_copy(
        update={"mode": "provisional", "research_signals": None}
    )

    result = plan_component_strategy(request)

    assert result.status == "planned"
    assert result.plan is None
    assert result.hypotheses
    assert result.research_questions


def test_final_vocabulary_plan_selects_diverse_renderable_components() -> None:
    result = plan_component_strategy(_request(subject="language", artifact_types=("lesson",)))

    assert result.status == "planned"
    assert result.plan is not None
    selected_components = {
        slot.component_type for slot in result.plan.recommended.learning_sequence
    }
    assert selected_components >= {"contrastive_pairs", "vocab_cluster"}
    assert result.plan.recommended.quality_score.audit_ledger["udl_coverage"] >= 0.0


def test_exam_prep_plan_uses_assessment_component() -> None:
    result = plan_component_strategy(
        _request(
            subject="math",
            artifact_types=("quiz",),
            assessment_intent=("exam_prep",),
        )
    )

    assert result.status == "planned"
    assert result.plan is not None
    assert result.plan.recommended.strategy_family_id == "exam_assessment_prep"
    assert result.plan.recommended.learning_sequence[0].component_type == "question_list"


def test_concept_plan_uses_math_science_strategy_family() -> None:
    result = plan_component_strategy(_request(subject="science", artifact_types=("lesson",)))

    assert result.status == "planned"
    assert result.plan is not None
    assert result.plan.recommended.strategy_family_id == "concept_math_science"
    assert {slot.component_type for slot in result.plan.recommended.learning_sequence} == {"flow_step"}


def test_conflicting_teacher_rejection_blocks_with_typed_result() -> None:
    teacher_preferences = TeacherPreferenceSignals(
        feedback_events=(
            StrategyFeedbackEvent(
                event_id="fb-1",
                event_type="reject_component_family",
                source="teacher",
                value="vocabulary_language",
            ),
        )
    )

    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
            teacher_preferences=teacher_preferences,
        )
    )

    assert result.status == "blocked"
    assert result.plan is None
    assert result.blocking_issues[0].code == "feedback_conflict"
    assert result.blocking_issues[0].teacher_options


def test_rejected_component_uses_reviewed_fallback_when_strategy_remains() -> None:
    teacher_preferences = TeacherPreferenceSignals(
        feedback_events=(
            StrategyFeedbackEvent(
                event_id="fb-1",
                event_type="reject_component_family",
                source="teacher",
                value="contrastive_pairs",
            ),
        )
    )

    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
            teacher_preferences=teacher_preferences,
        )
    )

    assert result.status == "planned_with_fallback"
    assert result.plan is not None
    assert result.plan.recommended.fallback_metadata is not None
    assert result.plan.recommended.fallback_metadata.original_component_type == "contrastive_pairs"
    assert result.plan.recommended.fallback_metadata.fallback_component_type == "table"
    assert result.plan.revision is not None
    assert result.plan.revision.materiality == "teacher_visible"
    assert result.plan.revision.teacher_reapproval_required is True


def test_implicit_rejection_relaxes_with_audit_warning() -> None:
    teacher_preferences = TeacherPreferenceSignals(
        feedback_events=(
            StrategyFeedbackEvent(
                event_id="pref-1",
                event_type="reject_component_family",
                source="system",
                value="vocab_cluster",
            ),
        )
    )

    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
            teacher_preferences=teacher_preferences,
        )
    )

    assert result.status == "planned"
    assert result.plan is not None
    assert result.warnings[0].code == "fallback_used"
    assert result.warnings[0].message.startswith("Relaxed implicit")


def test_no_valid_component_blocks_instead_of_throwing() -> None:
    result = plan_component_strategy(_request(subject="language", artifact_types=("answer_key",)))

    assert result.status == "blocked"
    assert result.plan is None
    assert result.blocking_issues[0].code == "no_eligible_component"


def test_selector_output_validates_as_component_strategy_result() -> None:
    result = plan_component_strategy(_request(subject="language", artifact_types=("lesson",)))

    reparsed = ComponentStrategyResult.model_validate(result.model_dump())

    assert reparsed == result


def test_uncovered_core_objective_blocks_with_typed_options() -> None:
    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
            objective_refs=(
                _objective("LO-core", assessable=False),
                _objective("LO-extension", importance="extension", assessable=False),
            ),
        )
    )

    assert result.status == "blocked"
    assert result.blocking_issues[0].code == "core_objective_uncovered"
    assert "LO-core" in result.blocking_issues[0].affected_objective_ids


def test_extension_objective_deferral_is_visible_non_blocking_note() -> None:
    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
            objective_refs=(_objective("LO-extension", importance="extension", assessable=False),),
        )
    )

    assert result.status == "planned"
    assert result.plan is not None
    assert result.plan.objective_coverage[0].coverage_state == "deferred"
    assert result.warnings[0].code == "objective_deferred"


def test_homework_delivery_reduces_teacher_load_and_sets_self_check() -> None:
    result = plan_component_strategy(
        _request(
            subject="language",
            artifact_types=("lesson",),
        ).model_copy(update={"delivery": {"mode": "homework", "inference_reason": "teacher selected homework"}})
    )

    assert result.plan is not None
    slot = result.plan.recommended.learning_sequence[0]
    assert result.plan.delivery_context.mode == "homework"
    assert slot.scoring_intent.mode == "self_check"
    assert slot.budget.teacher_load_level == "low"


def test_summative_quiz_sets_auto_gradable_scoring_intent() -> None:
    result = plan_component_strategy(_request(subject="math", artifact_types=("quiz",), assessment_intent=("summative",)))

    assert result.plan is not None
    slot = result.plan.recommended.learning_sequence[0]
    assert slot.scoring_intent.assessment_intent == "summative"
    assert slot.scoring_intent.mode == "auto_gradable"
    assert slot.scoring_intent.partial_credit_allowed is True


def test_scaffoldable_prerequisite_gap_adds_budgeted_scaffold_slot() -> None:
    result = plan_component_strategy(
        _request(subject="language", artifact_types=("lesson",)).model_copy(
            update={"research_signals": _research().model_copy(update={"prerequisite_risk": "missing_scaffoldable"})}
        )
    )

    assert result.plan is not None
    scaffold = result.plan.recommended.learning_sequence[0]
    assert scaffold.learning_move_id == "prerequisite_scaffold"
    assert scaffold.parent_slot_id is None
    assert scaffold.budget.max_time_minutes <= 8


def test_blocking_prerequisite_gap_returns_typed_replan_options() -> None:
    result = plan_component_strategy(
        _request(subject="language", artifact_types=("lesson",)).model_copy(
            update={"research_signals": _research().model_copy(update={"prerequisite_risk": "missing_blocking"})}
        )
    )

    assert result.status == "blocked"
    assert result.blocking_issues[0].code == "prerequisite_missing"
    assert "add_prerequisite_pack" in result.blocking_issues[0].teacher_options


def test_misconception_probe_slots_require_distractor_mapping_without_text() -> None:
    result = plan_component_strategy(_request(subject="language", artifact_types=("lesson",)))

    assert result.plan is not None
    slot = result.plan.recommended.learning_sequence[0]
    assert "distractor_coverage_mapping_required" in slot.fill_requirements
    assert "exact_distractor_text" in slot.forbidden_fill_patterns


def test_large_class_teacher_load_affects_score_audit() -> None:
    result = plan_component_strategy(
        _request(subject="language", artifact_types=("lesson",)).model_copy(
            update={"delivery_context": {"class_size": 48, "teacher_prep_load": "high"}}
        )
    )

    assert result.plan is not None
    assert result.plan.audit_score_ledger["teacher_load_multiplier"] < 1.0


def test_artifact_recommendation_is_visible_without_changing_scope() -> None:
    result = plan_component_strategy(_request(subject="language", artifact_types=("lesson",), assessment_intent=("exam_prep",)))

    assert result.plan is not None
    assert result.plan.recommended.artifact_strategies[0].artifact_type == "lesson"
    assert result.plan.artifact_scope_recommendations[0].teacher_visible is True
