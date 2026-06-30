from __future__ import annotations

from common.contracts.lesson_sequence import KnowledgeComponent, LessonSequence, SessionPlan
from packages.agents.middleware.sequence_consistency_validator import (
    ConsistencySeverity,
    SequenceConsistencyValidator,
)
from packages.agents.teaching_pack.quality_routing import quality_recovery_route


def _session(session_id: str, order_index: int, prereqs: list[str] | None = None) -> SessionPlan:
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=f"Session {order_index}",
        sub_topic=f"Topic {order_index}",
        duration_minutes=45,
        learning_objectives=["Understand and apply the concept"],
        bloom_level_primary="apply",
        knowledge_components=[KnowledgeComponent(
            kc_id=f"KC-{order_index}",
            title=f"KC {order_index}",
            description="A knowledge component",
        )],
        prerequisite_sessions=prereqs or [],
        methodology_primary="concept_map",
    )


def test_sequence_validator_emits_hard_issue_before_unit_gate() -> None:
    sequence = LessonSequence(
        topic="Fractions",
        grade_level="Grade 5",
        subject="math",
        locale="vi-VN",
        total_sessions=2,
        total_duration_minutes=90,
        sessions=[_session("S01", 1, ["S02"]), _session("S02", 2, ["S01"])],
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test sequence",
    )

    issues = SequenceConsistencyValidator().validate(sequence)

    assert any(issue.rule == "cycle" and issue.severity is ConsistencySeverity.HARD for issue in issues)


def test_healing_route_sends_factual_uncertainty_back_to_research() -> None:
    route = quality_recovery_route(["pack.coherence:factual_uncertainty: source mismatch"])

    assert route == "post_blueprint_research"
