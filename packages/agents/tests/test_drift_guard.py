from __future__ import annotations

import pytest

from common.contracts.lesson_plan import LessonPlan
from common.contracts.lesson_sequence import SessionPlan
from packages.agents.sub_agents.planner.nodes import PlannerDriftError, ensure_seed_alignment


def test_drift_guard_rejects_added_objective() -> None:
    seed = SessionPlan.model_validate(_seed())
    plan_data = _plan().model_dump()
    plan_data["learning_objectives"] = [
        *plan_data["learning_objectives"],
        {"description": "Extra objective", "bloom_level": "apply"},
    ]
    plan = LessonPlan.model_validate(plan_data)

    with pytest.raises(PlannerDriftError, match="objective_added"):
        ensure_seed_alignment(plan, seed)


def test_drift_guard_accepts_faithful_expansion() -> None:
    ensure_seed_alignment(_plan(), SessionPlan.model_validate(_seed()))


def _seed() -> dict[str, object]:
    return {
        "session_id": "S01",
        "order_index": 1,
        "title": "Apply fractions",
        "sub_topic": "Fraction application",
        "duration_minutes": 45,
        "learning_objectives": ["Students can apply fractions"],
        "bloom_level_primary": "apply",
        "knowledge_components": [
            {"kc_id": "KC-FRAC-EQ", "title": "Fraction equivalence", "description": "Equivalent fractions"},
        ],
        "recalled_kc_ids": [],
        "prerequisite_sessions": [],
        "methodology_primary": "timed_quiz",
    }


def _plan() -> LessonPlan:
    return LessonPlan.model_validate({
        "topic": "Fraction application",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 45,
        "learning_objectives": [
            {"description": "Students can apply fractions", "bloom_level": "apply"},
        ],
        "prerequisite_knowledge": ["Fraction equivalence"],
        "learning_plan": {"present_content": "KC-FRAC-EQ"},
        "assessment_checkpoints": [],
    })
