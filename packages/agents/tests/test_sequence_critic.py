from __future__ import annotations

from common.contracts.lesson_sequence import LessonSequence
from packages.agents.sub_agents.unit_planner.sequence_critic import (
    CritiqueSeverity,
    CritiqueType,
    critique_sequence,
    repair_hard_critiques,
)


def test_sequence_critic_reports_ordering_when_apply_precedes_remember() -> None:
    sequence = LessonSequence.model_validate(_sequence([
        ("S01", 1, "apply", "Fractions practice"),
        ("S02", 2, "remember", "Fraction vocabulary"),
    ]))

    critiques = critique_sequence(sequence)

    assert critiques[0].critique_type is CritiqueType.ORDERING
    assert critiques[0].severity is CritiqueSeverity.HARD
    assert critiques[0].involved_sessions == ("S01", "S02")


def test_sequence_critic_reports_fragmentation_for_duplicate_atomic_topic() -> None:
    sequence = LessonSequence.model_validate(_sequence([
        ("S01", 1, "remember", "Equivalent fractions"),
        ("S02", 2, "understand", "Equivalent fractions"),
    ]))

    critiques = critique_sequence(sequence)

    assert any(critique.critique_type is CritiqueType.FRAGMENTATION for critique in critiques)


def test_hard_ordering_repair_sorts_by_bloom_rank() -> None:
    sequence = LessonSequence.model_validate(_sequence([
        ("S01", 1, "apply", "Practice"),
        ("S02", 2, "remember", "Vocabulary"),
    ]))

    repaired = repair_hard_critiques(sequence)

    assert [session.bloom_level_primary for session in repaired.sessions] == ["remember", "apply"]


def _sequence(rows: list[tuple[str, int, str, str]]) -> dict[str, object]:
    return {
        "topic": "Fractions",
        "grade_level": "Grade 5",
        "subject": "math",
        "locale": "en",
        "total_sessions": len(rows),
        "total_duration_minutes": len(rows) * 45,
        "sessions": [
            {
                "session_id": session_id,
                "order_index": order,
                "title": title,
                "sub_topic": title,
                "duration_minutes": 45,
                "learning_objectives": [f"Students learn {title}"],
                "bloom_level_primary": bloom,
                "knowledge_components": [
                    {
                        "kc_id": f"KC-{session_id}",
                        "title": title,
                        "description": title,
                    },
                ],
                "recalled_kc_ids": [],
                "prerequisite_sessions": [],
                "methodology_primary": "active_recall",
            }
            for session_id, order, bloom, title in rows
        ],
        "prerequisite_edges": [],
        "grounding_status": "grounded",
        "confidence": 0.9,
        "open_questions": [],
        "low_confidence_decisions": [],
        "rationale": "test",
    }
