from __future__ import annotations

import pytest

from common.contracts.lesson_sequence import LessonSequence
from packages.agents.middleware.sequence_consistency_validator import (
    ConsistencySeverity,
    SequenceConsistencyValidator,
)
from packages.agents.sub_agents.unit_planner import ClarificationRequiredError, unit_planner_node
from packages.agents.teaching_pack.stages import StageEnum


@pytest.mark.asyncio
async def test_unit_planner_outputs_grounded_valid_sequence() -> None:
    result = await unit_planner_node({
        "raw_request": "Plan a unit about Phân số",
        "class_info": {"grade": 5, "subject": "math", "student_count": 30, "topic": "Phân số"},
        "grounding": {"grounding_status": "grounded"},
        "run_id": "run-unit-1",
        "current_step": StageEnum.UNIT_PLANNING,
    })

    sequence = LessonSequence.model_validate(result["lesson_sequence"])
    issues = SequenceConsistencyValidator().validate(sequence)

    assert sequence.grounding_status == "grounded"
    assert 2 <= sequence.total_sessions <= 6
    assert len({session.bloom_level_primary for session in sequence.sessions}) >= 2
    assert all(len(session.knowledge_components) <= 4 for session in sequence.sessions)
    assert [issue for issue in issues if issue.severity is ConsistencySeverity.HARD] == []


@pytest.mark.asyncio
async def test_methodology_assignment_varies_by_bloom_level() -> None:
    result = await unit_planner_node({
        "raw_request": "Plan fractions",
        "class_info": {"grade": 5, "subject": "math", "student_count": 30, "topic": "Fractions"},
        "grounding": {"grounding_status": "grounded"},
        "run_id": "run-unit-2",
        "current_step": StageEnum.UNIT_PLANNING,
    })

    sequence = LessonSequence.model_validate(result["lesson_sequence"])
    methods_by_bloom = {
        session.bloom_level_primary: session.methodology_primary for session in sequence.sessions
    }

    assert methods_by_bloom["remember"] == "active_recall"
    assert methods_by_bloom["apply"] == "timed_quiz"


@pytest.mark.asyncio
async def test_ungrounded_ambiguous_topic_fails_closed() -> None:
    with pytest.raises(ClarificationRequiredError):
        await unit_planner_node({
            "raw_request": "Math",
            "class_info": {"grade": 5, "subject": "math", "student_count": 30},
            "grounding": {"grounding_status": "ungrounded"},
            "run_id": "run-unit-3",
            "current_step": StageEnum.UNIT_PLANNING,
        })


@pytest.mark.asyncio
async def test_persona_changes_reteach_and_duration_decisions() -> None:
    base = {
        "raw_request": "Plan a unit about Fractions",
        "class_info": {"grade": 5, "subject": "math", "student_count": 30, "topic": "Fractions"},
        "grounding": {"grounding_status": "partial"},
        "run_id": "run-unit-4",
        "current_step": StageEnum.UNIT_PLANNING,
    }
    weak_persona = {
        "grade": "Grade 5",
        "age_band": "upper_primary",
        "subject_focus": "math",
        "language": "en",
        "class_size": 30,
        "proficiency_level": "developing",
        "attention_span_band": "short",
        "prior_knowledge_gaps": ["equivalent fractions"],
    }
    advanced_persona = {
        **weak_persona,
        "proficiency_level": "advanced",
        "attention_span_band": "long",
        "prior_knowledge_gaps": [],
    }

    weak = LessonSequence.model_validate((await unit_planner_node({**base, "persona_snapshot": weak_persona}))["lesson_sequence"])
    advanced = LessonSequence.model_validate((await unit_planner_node({**base, "persona_snapshot": advanced_persona}))["lesson_sequence"])

    assert weak.sessions[0].duration_minutes == 30
    assert advanced.sessions[0].duration_minutes == 60
    assert weak.sessions[0].sub_topic.startswith("Reteach")
    assert advanced.sessions[0].bloom_level_primary == "understand"
