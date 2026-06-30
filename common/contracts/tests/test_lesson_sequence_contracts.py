from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.lesson_sequence import (
    KnowledgeComponent,
    LessonSequence,
    PrerequisiteEdge,
    SessionPlan,
)


def _kc(kc_id: str, title: str) -> KnowledgeComponent:
    return KnowledgeComponent(kc_id=kc_id, title=title, description=f"Understand {title}")


def _session(session_id: str, order_index: int, title: str) -> SessionPlan:
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=title,
        sub_topic=title,
        duration_minutes=45,
        learning_objectives=[f"Explain {title}"],
        bloom_level_primary="understand",
        knowledge_components=[_kc(f"KC-{session_id}", title)],
        recalled_kc_ids=[],
        prerequisite_sessions=[],
        methodology_primary="active_recall",
    )


def _sequence(topic: str, subject: str, sessions: list[SessionPlan]) -> LessonSequence:
    return LessonSequence(
        topic=topic,
        grade_level="Lớp 5",
        subject=subject,
        locale="vi-VN",
        total_sessions=len(sessions),
        total_duration_minutes=sum(session.duration_minutes for session in sessions),
        sessions=sessions,
        prerequisite_edges=[
            PrerequisiteEdge(source_kc_id="KC-S01", target_kc_id="KC-S02", rationale="Builds next")
        ],
        grounding_status="grounded",
        confidence=0.84,
        open_questions=[],
        rationale="Sequence follows prerequisite order.",
    )


def test_valid_fixtures_parse_and_round_trip_when_multi_session_topics() -> None:
    vn_math = _sequence(
        "Phân số",
        "math",
        [_session("S01", 1, "Khái niệm phân số"), _session("S02", 2, "So sánh phân số")],
    )
    english = LessonSequence(
        **_sequence(
            "Present perfect vs past simple",
            "english",
            [_session("S01", 1, "Signal words"), _session("S02", 2, "Contrastive practice")],
        ).model_dump()
    )
    science = LessonSequence(
        **_sequence(
            "Food chains",
            "science",
            [_session("S01", 1, "Producers"), _session("S02", 2, "Consumers")],
        ).model_dump()
    )

    for sequence in (vn_math, english, science):
        dumped = sequence.model_dump()
        reparsed = LessonSequence.model_validate(dumped)
        assert reparsed == sequence


def test_session_rejects_excessive_cognitive_load_when_more_than_four_new_kcs() -> None:
    with pytest.raises(ValidationError):
        SessionPlan(
            **{
                **_session("S01", 1, "Fractions").model_dump(),
                "knowledge_components": [_kc(f"KC-{index}", str(index)) for index in range(5)],
            }
        )


def test_session_rejects_invalid_duration_and_empty_learning_objectives() -> None:
    with pytest.raises(ValidationError):
        SessionPlan(
            **{
                **_session("S01", 1, "Fractions").model_dump(),
                "duration_minutes": 9,
            }
        )
    with pytest.raises(ValidationError):
        SessionPlan(
            **{
                **_session("S01", 1, "Fractions").model_dump(),
                "learning_objectives": [],
            }
        )


def test_sequence_rejects_unknown_prerequisite_session_but_preserves_stable_ids_on_reorder() -> None:
    first = _session("S01", 2, "Concept")
    second = SessionPlan(
        **{
            **_session("S02", 1, "Practice").model_dump(),
            "prerequisite_sessions": ["S01"],
        }
    )
    reordered = _sequence("Fractions", "math", [second, first])
    assert reordered.sessions[0].prerequisite_sessions == ["S01"]

    with pytest.raises(ValidationError):
        LessonSequence(
            **{
                **reordered.model_dump(),
                "sessions": [
                    {**second.model_dump(), "prerequisite_sessions": ["S99"]},
                    first.model_dump(),
                ],
            }
        )
