from __future__ import annotations

from common.contracts.lesson_sequence import LessonSequence
from packages.agents.sub_agents.unit_planner.class_knowledge_graph import (
    ClassKnowledgeGraph,
    class_knowledge_graph_from_edges,
)


def test_approved_sequence_builds_expected_edges() -> None:
    graph = ClassKnowledgeGraph(teacher_id="teacher-1", class_id="class-5a")

    graph.add_approved_sequence(_sequence())

    assert graph.as_edge_list() == [
        {"source_kc_id": "KC-S01", "target_kc_id": "KC-S02"},
    ]


def test_query_returns_covered_and_missing_prerequisites() -> None:
    graph = class_knowledge_graph_from_edges(
        "teacher-1",
        "class-5a",
        [{"source_kc_id": "KC-S01", "target_kc_id": "KC-S02"}],
    )

    result = graph.query_prerequisites(("KC-S02", "KC-S03"))

    assert result.covered_kc_ids == ("KC-S02",)
    assert result.missing_prerequisite_kc_ids == ()
    assert result.redundant_kc_ids == ("KC-S02",)


def _sequence() -> LessonSequence:
    return LessonSequence.model_validate({
        "topic": "Fractions",
        "grade_level": "Grade 5",
        "subject": "math",
        "locale": "en",
        "total_sessions": 2,
        "total_duration_minutes": 90,
        "sessions": [
            _session("S01", 1, "remember"),
            _session("S02", 2, "understand"),
        ],
        "prerequisite_edges": [],
        "grounding_status": "grounded",
        "confidence": 0.9,
        "open_questions": [],
        "low_confidence_decisions": [],
        "rationale": "test",
    })


def _session(session_id: str, order: int, bloom: str) -> dict[str, object]:
    return {
        "session_id": session_id,
        "order_index": order,
        "title": session_id,
        "sub_topic": session_id,
        "duration_minutes": 45,
        "learning_objectives": [session_id],
        "bloom_level_primary": bloom,
        "knowledge_components": [{"kc_id": f"KC-{session_id}", "title": session_id, "description": session_id}],
        "recalled_kc_ids": [],
        "prerequisite_sessions": [],
        "methodology_primary": "active_recall",
    }
