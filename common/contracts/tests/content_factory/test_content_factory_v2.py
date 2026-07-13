from __future__ import annotations

import pytest

from common.contracts.content_factory.assessment import (
    AssessmentVerificationError,
    build_item_blueprints,
    validate_question_card,
)
from common.contracts.content_factory.coherence import evaluate_pack_coherence
from common.contracts.content_factory.instructional_design import build_instructional_design_plan
from common.contracts.content_factory.orchestration import build_content_brief, request_from_payload
from common.contracts.content_factory.synthesis import (
    PrerequisiteCycleError,
    build_synthesis_plan,
    prerequisite_order,
    visual_semantics,
)
from common.contracts.content_factory.tenancy import (
    TenantAccessDeniedError,
    TenantContext,
    privacy_safe_metadata,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "duration_minutes": 45,
        "methodology": "concrete-representational-abstract",
        "terminology": ["equivalent fraction"],
        "learning_objectives": [
            {
                "objective_id": "obj-identify",
                "description": "Identify equivalent fractions.",
                "bloom_level": "understand",
            },
            {
                "objective_id": "obj-generate",
                "description": "Generate an equivalent fraction.",
                "bloom_level": "apply",
            },
        ],
        "learning_plan": {
            "launch": "Compare two fraction strips and predict whether they show the same amount.",
            "model": "Model one equivalence and name the invariant.",
            "practice": "Create and justify a new equivalent fraction.",
            "closure": "Explain why multiplying numerator and denominator by the same factor preserves value.",
        },
    }


def _research_brief() -> dict[str, object]:
    return {
        "content_intelligence": {
            "snapshot_version": "objective-graph-deadbeef",
            "terminology": ["numerator", "denominator"],
            "objective_decomposition": {
                "snapshot_version": "objective-graph-deadbeef",
                "nodes": [
                    {
                        "objective_id": "obj-identify",
                        "description": "Identify equivalent fractions.",
                        "knowledge_component_ids": ["kc-fraction-value", "kc-common-factor"],
                    },
                    {
                        "objective_id": "obj-generate",
                        "description": "Generate an equivalent fraction.",
                        "knowledge_component_ids": ["kc-scale-numerator", "kc-scale-denominator"],
                    },
                ],
            },
        },
        "sources": [
            {
                "source_id": "source-a",
                "title": "Guide A",
                "excerpt": "Equivalent fractions name the same value.",
                "claim_id": "claim-equivalence",
                "verification_status": "verified",
            },
            {
                "source_id": "source-b",
                "title": "Guide B",
                "excerpt": "Equivalent fractions name the same value.",
                "claim_id": "claim-equivalence",
                "verification_status": "verified",
            },
        ],
    }


def test_content_brief_uses_live_graph_decomposition_and_pins_snapshot() -> None:
    brief = build_content_brief(
        run_id="run-1",
        artifact_type="lesson",
        lesson_plan=_lesson_plan(),
        research_brief=_research_brief(),
        dependency_document_ids=["doc-a"],
    )

    assert brief.knowledge_db_version == "objective-graph-deadbeef"
    assert brief.scope == [
        "kc-fraction-value",
        "kc-common-factor",
        "kc-scale-numerator",
        "kc-scale-denominator",
    ]
    assert brief.dependency_document_ids == ["doc-a"]
    assert brief.source_citation_ids == ["source-a", "source-b"]


def test_orchestrator_request_rejects_cross_artifact_content_brief() -> None:
    payload = {
        "run_id": "run-1",
        "artifact_generation_id": "run-1:artifact:1",
        "artifact_type": "quiz",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "content_brief": build_content_brief(
            run_id="run-1",
            artifact_type="lesson",
            lesson_plan=_lesson_plan(),
            research_brief=_research_brief(),
        ).model_dump(mode="json"),
        "tenant": {
            "organization_id": "school-1",
            "principal_id": "teacher-1",
            "principal_role": "teacher",
            "teacher_id": "teacher-1",
        },
    }

    with pytest.raises(ValueError, match="artifact_type"):
        request_from_payload(payload)


def test_instructional_design_is_observable_and_time_bounded() -> None:
    plan = build_instructional_design_plan(_lesson_plan())

    assert plan.allocated_minutes + plan.transition_reserve_minutes + plan.contingency_minutes <= 45
    assert set(plan.objective_ids) == {"obj-identify", "obj-generate"}
    assert all(phase.teacher_actions for phase in plan.phases)
    assert all(phase.student_actions for phase in plan.phases)
    assert all(phase.checks_for_understanding for phase in plan.phases)
    assert all(phase.anticipated_responses for phase in plan.phases)
    assert all(phase.misconception_responses for phase in plan.phases)
    assert all(phase.differentiation for phase in plan.phases)
    assert all(phase.transition and phase.closure for phase in plan.phases)


def test_assessment_blueprints_cover_objective_misconception_and_solver_authority() -> None:
    blueprints = build_item_blueprints(
        _lesson_plan(),
        count=6,
        response_type="selected_response",
        practice=True,
    )

    assert [blueprint.practice_stage for blueprint in blueprints] == [
        "worked_example",
        "guided",
        "independent",
        "retrieval",
        "interleaved",
        "transfer",
    ]
    assert all(blueprint.verification_method == "solver" for blueprint in blueprints)
    assert all(blueprint.misconception_target_id for blueprint in blueprints)
    assert all(blueprint.evidence_statement_id for blueprint in blueprints)


def test_assessment_verification_rejects_duplicate_distractor_collision() -> None:
    blueprint = build_item_blueprints(
        _lesson_plan(),
        count=1,
        response_type="selected_response",
        practice=False,
    )[0]
    with pytest.raises(AssessmentVerificationError, match="duplicate option"):
        validate_question_card({
            "options": {"A": "1/2", "B": "1/2", "C": "2/3"},
            "answer": "A",
            "verification": {"trace": "solver"},
        }, blueprint)


def test_synthesis_triangulates_material_claims_and_has_no_image_fallback() -> None:
    plan = build_synthesis_plan(
        _lesson_plan(),
        _research_brief(),
        target_length_words=120,
    )
    source_claim = next(claim for claim in plan.retained_claims if claim.claim_id == "claim-equivalence")

    assert source_claim.authority == "verified"
    assert source_claim.evidence_ids == ("source-a", "source-b")
    assert not any("claim-equivalence" in warning for warning in plan.warnings)
    visuals = visual_semantics(plan)
    assert all(visual["grayscale_safe"] for visual in visuals)
    assert all(visual["alt_text"] == visual["no_image_fallback"] for visual in visuals)
    assert all("Evidence:" in visual["long_description"] for visual in visuals)


def test_prerequisite_order_fails_closed_on_cycle() -> None:
    with pytest.raises(PrerequisiteCycleError):
        prerequisite_order(["a", "b"], [("a", "b"), ("b", "a")])


def test_pack_coherence_uses_stable_ids_not_paraphrase_similarity() -> None:
    report = evaluate_pack_coherence([
        {
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "sections": [{"content": "Fractions with equal value."}],
            "metadata": {
                "approved_objective_ids": ["obj-identify"],
                "objective_lineage": [{"objective_id": "obj-identify", "description": "Identify equivalent fractions."}],
                "knowledge_db_version": "graph-v1",
            },
        },
        {
            "artifact_id": "recap-1",
            "artifact_type": "recap",
            "sections": [{"content": "Different words, same approved objective."}],
            "metadata": {
                "objective_lineage": [{"objective_id": "obj-identify", "description": "Spot fractions that are equal."}],
                "knowledge_db_version": "graph-v1",
            },
        },
    ])

    assert report.passed is True
    assert report.findings == ()


def test_pack_coherence_blocks_unknown_objective_leakage_and_mixed_snapshot() -> None:
    report = evaluate_pack_coherence([
        {
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "sections": [{"content": "Approved lesson"}],
            "metadata": {
                "approved_objective_ids": ["obj-identify"],
                "knowledge_db_version": "graph-v1",
            },
        },
        {
            "artifact_id": "quiz-1",
            "artifact_type": "quiz",
            "sections": [{"components": [{"answer": "A"}]}],
            "metadata": {
                "item_blueprints": [{"objective_id": "obj-unapproved"}],
                "knowledge_db_version": "graph-v2",
            },
        },
    ])

    assert report.passed is False
    assert {finding.code for finding in report.findings} == {
        "unknown_objective_lineage",
        "student_projection_leakage",
        "mixed_knowledge_snapshot",
    }
    assert report.blocked_exports == ("composite_export", "live_publication")


def test_tenant_context_denies_cross_org_and_redacts_content_telemetry() -> None:
    tenant = TenantContext(
        organization_id="school-1",
        principal_id="teacher-1",
        principal_role="teacher",
        teacher_id="teacher-1",
    )

    assert tenant.storage_key("artifacts", "run-1", "lesson-1") == (
        "organizations/school-1/artifacts/run-1/lesson-1"
    )
    with pytest.raises(TenantAccessDeniedError):
        tenant.require_organization("school-2")

    redacted = privacy_safe_metadata({
        "run_id": "run-1",
        "content": "student name and full generated lesson",
        "nested": {"answer": "A", "status": "passed"},
    })
    assert redacted["run_id"] == "run-1"
    assert redacted["content"]["redacted"] is True
    assert redacted["nested"]["answer"]["redacted"] is True
    assert redacted["nested"]["status"] == "passed"
