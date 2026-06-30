from __future__ import annotations

import pytest

from common.contracts.lesson_sequence import LessonSequence
from packages.agents.sub_agents.unit_planner import unit_planner_node


@pytest.mark.asyncio
async def test_teacher_preference_prior_softly_changes_duration() -> None:
    result = await unit_planner_node({
        "raw_request": "Plan a unit about Fractions",
        "class_info": {"grade": 5, "subject": "math", "student_count": 30, "topic": "Fractions"},
        "grounding": {"grounding_status": "grounded"},
        "teacher_preferences": {"preferred_session_duration_minutes": 25},
        "run_id": "run-prior",
        "current_step": 1,
    })

    sequence = LessonSequence.model_validate(result["lesson_sequence"])

    assert {session.duration_minutes for session in sequence.sessions} == {25}
    assert "teacher decomposition-memory duration prior applied softly" in sequence.low_confidence_decisions
