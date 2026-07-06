from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.component_strategy import (
    ArtifactStrategyProjection,
    ComponentStrategyPlan,
    ComponentStrategyRequest,
    ComponentStrategyResult,
    ObjectiveRef,
    ResearchSignals,
    StrategyFeedbackEvent,
    StrategyQualityScore,
    StrategySlot,
    StrategySlotBudget,
    StrategyVariant,
)
from common.contracts.component_strategy_slot_contracts import (
    StrategyAssessmentIntent,
    StrategyDeliveryContext,
    StrategyDeliveryMode,
    StrategyScoringMode,
)
from common.contracts.component_strategy_privacy import StrategyDecisionLedger, StrategyRequestFingerprint


def _objective_ref() -> ObjectiveRef:
    return ObjectiveRef(objective_id="LO-1", objective_revision="rev-1")


def _slot() -> StrategySlot:
    return StrategySlot(
        slot_id="strat-run-1/lesson/slot-1",
        sequence_id="seq-1",
        phase="activate",
        learning_move_id="misconception_probe",
        component_type="multiple_choice_single",
        component_binding_id="mcq-misconception-probe@1.0.0",
        objective_refs=(_objective_ref(),),
        target_artifacts=("lesson",),
        required_affordances=("diagnose_error",),
        fill_requirements=("distractors_must_map_to_misconceptions",),
        forbidden_fill_patterns=("random_wrong_answers",),
        budget=StrategySlotBudget(
            ideal_time_minutes=5,
            max_time_minutes=7,
            ideal_item_count=1,
            max_item_count=2,
        ),
    )


def _projection() -> ArtifactStrategyProjection:
    return ArtifactStrategyProjection(
        artifact_type="lesson",
        ordered_slot_ids=("strat-run-1/lesson/slot-1",),
    )


def _quality_score() -> StrategyQualityScore:
    return StrategyQualityScore(
        overall=0.82,
        objective_alignment=0.9,
        evidence_signal_coverage=0.8,
        component_diversity=0.7,
        compliance_safety="pass",
    )


def _variant() -> StrategyVariant:
    return StrategyVariant(
        variant_id="recommended",
        strategy_family_id="evidence_balanced_default",
        display_label="Recommended",
        learning_sequence=(_slot(),),
        artifact_strategies=(_projection(),),
        quality_score=_quality_score(),
    )


def _plan() -> ComponentStrategyPlan:
    return ComponentStrategyPlan(
        strategy_id="strategy-run-1-rev-1",
        strategy_schema_version="component_strategy.v1",
        knowledge_db_version="2026.07.05",
        selector_version="selector.v1",
        scoring_profile_id="evidence_balanced_default",
        blueprint_revision_id="bp-rev-1",
        objective_refs=(_objective_ref(),),
        recommended=_variant(),
        variants=(),
        rationale_facts=("Objective LO-1 needs misconception probing.",),
        rationale_text="Start with a misconception probe before guided practice.",
    )


class TestComponentStrategyRequest:
    def test_parses_provisional_request_without_research_signals(self) -> None:
        request = ComponentStrategyRequest(
            mode="provisional",
            run_id="run-1",
            teacher_id_hash="teacher-hash",
            locale="vi",
            subject="math",
            grade_level="Grade 5",
            duration_minutes=45,
            artifact_types=("lesson", "worksheet"),
            export_formats=("html",),
            objective_refs=(_objective_ref(),),
        )

        assert request.mode == "provisional"
        assert request.research_signals is None

    def test_final_request_accepts_typed_research_signals(self) -> None:
        request = ComponentStrategyRequest(
            mode="final",
            run_id="run-1",
            teacher_id_hash="teacher-hash",
            locale="vi",
            subject="math",
            grade_level="Grade 5",
            duration_minutes=45,
            artifact_types=("lesson",),
            export_formats=("html",),
            objective_refs=(_objective_ref(),),
            research_signals=ResearchSignals(
                factual_risk="low",
                source_confidence="high",
                prerequisite_risk="met",
            ),
        )

        assert request.research_signals is not None
        assert request.research_signals.source_confidence == "high"

    def test_request_accepts_typed_delivery_context(self) -> None:
        request = ComponentStrategyRequest(
            mode="final",
            run_id="run-1",
            teacher_id_hash="teacher-hash",
            locale="vi",
            subject="math",
            grade_level="Grade 5",
            duration_minutes=45,
            artifact_types=("lesson",),
            export_formats=("html",),
            objective_refs=(_objective_ref(),),
            delivery=StrategyDeliveryContext(
                mode=StrategyDeliveryMode.HOMEWORK,
                inference_reason="teacher selected homework",
                teacher_override=True,
            ),
        )

        assert request.delivery.mode is StrategyDeliveryMode.HOMEWORK
        assert request.delivery.teacher_override is True

    def test_rejects_individual_student_fields_at_selector_boundary(self) -> None:
        with pytest.raises(ValidationError, match="student_names"):
            ComponentStrategyRequest(
                mode="final",
                run_id="run-1",
                teacher_id_hash="teacher-hash",
                locale="vi",
                subject="math",
                grade_level="Grade 5",
                duration_minutes=45,
                artifact_types=("lesson",),
                export_formats=("html",),
                objective_refs=(_objective_ref(),),
                delivery_context={"student_names": "An, Bình"},
            )

    def test_fingerprint_excludes_raw_text_and_pii_like_fields(self) -> None:
        request = ComponentStrategyRequest(
            mode="final",
            run_id="run-1",
            teacher_id_hash="teacher-hash",
            locale="vi",
            subject="math",
            grade_level="Grade 5",
            duration_minutes=47,
            artifact_types=("lesson",),
            export_formats=("html",),
            objective_refs=(_objective_ref(),),
            delivery_context={"class_context_tags": "mixed_readiness", "raw_teacher_text": "teach An fractions"},
            research_signals=ResearchSignals(factual_risk="low", source_confidence="high", prerequisite_risk="met"),
        )

        fingerprint = StrategyRequestFingerprint.from_request(
            request,
            knowledge_db_version="2026.07.05",
            scoring_profile_id="evidence_balanced_default",
            selector_version="selector.v1",
            renderer_capability_checksum="renderer-v1",
            exporter_capability_checksum="exporter-v1",
        )
        payload = fingerprint.model_dump()

        assert payload["duration_bucket"] == "45_59"
        assert "teach An fractions" not in repr(payload)
        assert "teacher-hash" not in repr(payload)

    def test_debug_ledger_redacts_pii_and_sets_ttl(self) -> None:
        ledger = StrategyDecisionLedger.from_debug_payload(
            run_id="run-1",
            payload={"teacher_note": "Student email an@example.com needs help", "score": 9},
        )

        assert ledger.contains_strategy_debug_data is True
        assert ledger.retention_ttl_days == 14
        assert "an@example.com" not in repr(ledger.redacted_payload)


class TestComponentStrategyPlan:
    def test_round_trips_through_model_dump(self) -> None:
        original = _plan()
        reparsed = ComponentStrategyPlan.model_validate(original.model_dump())

        assert reparsed == original

    def test_required_version_fields_cannot_be_missing(self) -> None:
        payload = _plan().model_dump()
        del payload["knowledge_db_version"]

        with pytest.raises(ValidationError):
            ComponentStrategyPlan.model_validate(payload)

    def test_plan_is_frozen(self) -> None:
        plan = _plan()

        with pytest.raises(ValidationError):
            plan.strategy_id = "changed"

    def test_slot_declares_scoring_and_fill_constraints(self) -> None:
        slot = _slot()

        assert slot.scoring_intent.assessment_intent is StrategyAssessmentIntent.FORMATIVE
        assert slot.scoring_intent.mode is StrategyScoringMode.SELF_CHECK
        assert "distractors_must_map_to_misconceptions" in slot.fill_requirements


class TestComponentStrategyResult:
    def test_blocked_result_carries_typed_issue_without_plan(self) -> None:
        result = ComponentStrategyResult(
            status="blocked",
            plan=None,
            blocking_issues=("core_objective_uncovered",),
            warnings=(),
        )

        assert result.status == "blocked"
        assert result.plan is None


class TestStrategyFeedbackEvent:
    def test_reject_component_family_is_typed_and_bounded(self) -> None:
        event = StrategyFeedbackEvent(
            event_id="feedback-1",
            event_type="reject_component_family",
            source="teacher",
            value="multiple_choice",
        )

        assert event.event_type == "reject_component_family"

    def test_unknown_feedback_event_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            StrategyFeedbackEvent(
                event_id="feedback-1",
                event_type="force_exact_component",
                source="teacher",
                value="timeline",
            )
