from __future__ import annotations

import pytest

from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node


@pytest.mark.asyncio
async def test_roadmap_milestones_compose_to_unit_inputs_without_content() -> None:
    result = await roadmap_node(_state())

    roadmap = result["roadmap_artifact"]
    units = result["unit_decomposition_inputs"]

    assert roadmap["metadata"]["generation_mode"] == "milestone_to_unit_macro"
    assert units[0]["mode"] == "plan_unit"
    assert "artifacts" not in units[0]


@pytest.mark.asyncio
async def test_roadmap_personalization_branches_on_traits_and_exam() -> None:
    shy = await roadmap_node(_state(student_profile={
        "student_id": "student-1",
        "learning_style": {"primary": "visual"},
        "personality_traits": [{"trait": "shy", "vn_name": "rụt rè", "teaching_principle": "low pressure"}],
        "target_exam": "IELTS",
        "study_duration_months": 2,
    }))
    depth = await roadmap_node(_state(student_profile={
        "student_id": "student-1",
        "learning_style": {"primary": "reading"},
        "personality_traits": [{"trait": "depth_oriented", "vn_name": "đào sâu", "teaching_principle": "explain why"}],
        "target_exam": "TOEIC",
        "study_duration_months": 2,
    }))

    shy_text = str(shy["roadmap_artifact"])
    depth_text = str(depth["roadmap_artifact"])

    assert "low-pressure" in shy_text
    assert "IELTS" in shy_text
    assert "explain why" in depth_text
    assert "TOEIC" in depth_text


@pytest.mark.asyncio
async def test_roadmap_focus_areas_derive_from_diagnostic_gaps() -> None:
    result = await roadmap_node(_state())

    focus_areas = result["roadmap_artifact"]["metadata"]["focus_areas"]

    assert focus_areas == ["Fraction equivalence"]


@pytest.mark.asyncio
async def test_roadmap_kt_mastery_update_shifts_milestones() -> None:
    low = await roadmap_node(_state(kt_mastery={"Fraction equivalence": {"mastery": 0.2, "confidence": "high"}}))
    high = await roadmap_node(_state(kt_mastery={"Fraction equivalence": {"mastery": 0.9, "confidence": "high"}}))

    assert low["roadmap_artifact"]["sections"][0]["title"] != high["roadmap_artifact"]["sections"][0]["title"]


def _state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "diagnostic_report": {
            "student_id": "student-1",
            "overall_error_rate": 0.6,
            "recommended_level": "B1",
            "knowledge_gaps": [
                {"category": "Fraction equivalence", "error_rate": 0.8, "severity": "critical", "question_ids": ["q1"]},
            ],
        },
        "student_profile": {
            "student_id": "student-1",
            "learning_style": {"primary": "visual"},
            "personality_traits": [{"trait": "film_learner", "vn_name": "phim", "teaching_principle": "video"}],
            "target_exam": "HSA",
            "study_duration_months": 2,
        },
        "run_id": "run-roadmap",
        "current_step": 0,
        "roadmap_artifact": None,
        "use_structured_roadmap": True,
    }
    state.update(overrides)
    return state
