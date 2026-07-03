from __future__ import annotations

import pytest

from common.contracts.lesson_plan import LessonPlan
from packages.agents.sub_agents.planner.nodes import planner_node
from packages.agents.teaching_pack.stages import StageEnum


@pytest.mark.asyncio
async def test_expand_mode_preserves_seed_constraints() -> None:
    result = await planner_node({
        "raw_request": "Generate child lesson",
        "class_info": {"grade": "Grade 5", "subject": "math"},
        "run_id": "run-expand",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "lesson_plan": None,
        "seed": _seed(),
    })

    plan = LessonPlan.model_validate(result["lesson_plan"])

    assert plan.duration_minutes == 45
    assert {objective.description for objective in plan.learning_objectives} == {"Students can apply fractions"}
    assert {objective.bloom_level for objective in plan.learning_objectives} == {"apply"}
    assert set(plan.prerequisite_knowledge) == {"Fraction equivalence"}
    assert "present_content" in plan.learning_plan


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
