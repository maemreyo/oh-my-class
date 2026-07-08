from __future__ import annotations

import pytest

from common.contracts.lesson_plan import LessonPlan
from packages.agents.sub_agents.planner.lesson_consistency_validator import (
    LessonConsistencySeverity,
    LessonConsistencyValidator,
)
from packages.agents.sub_agents.planner.lesson_critic import CritiqueSeverity, critique_lesson
from packages.agents.sub_agents.planner.nodes import planner_node
from packages.agents.sub_agents.planner.staged_engine import has_curriculum_coverage
from packages.agents.teaching_pack.stages import StageEnum


def test_has_curriculum_coverage_true_for_parseable_grade() -> None:
    """LIC-04: a request with a parseable grade gets at least partial grounding."""
    assert has_curriculum_coverage({
        "raw_request": "Teach equivalent fractions",
        "class_info": {"grade_band": "Grade 5", "subject": "math", "language": "en", "topic": "Fractions"},
    })


def test_has_curriculum_coverage_false_for_unparseable_grade() -> None:
    """LIC-04: the real fallback condition (ADR-048) — an unparseable grade has
    nothing curriculum-specific to template against, so the planner should route
    to the real LLM branch instead of a generic boilerplate staged plan."""
    assert not has_curriculum_coverage({
        "raw_request": "Teach something",
        "class_info": {"grade_band": "Unknown", "subject": "general", "language": "en"},
    })


@pytest.mark.asyncio
async def test_staged_planner_builds_assessment_first_valid_plan() -> None:
    result = await planner_node({
        "raw_request": "Dạy phân số lớp 5",
        "class_info": {
            "grade": "Lớp 5",
            "subject": "toan",
            "student_count": 32,
            "language": "vi-VN",
            "topic": "Phân số",
        },
        "run_id": "run-staged",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "use_staged_planner": True,
    })

    plan = LessonPlan.model_validate(result["lesson_plan"])
    hard_issues = [
        issue
        for issue in LessonConsistencyValidator().validate(plan)
        if issue.severity is LessonConsistencySeverity.HARD
    ]
    hard_critiques = [
        critique for critique in critique_lesson(plan) if critique.severity is CritiqueSeverity.HARD
    ]

    assert len({objective.bloom_level for objective in plan.learning_objectives}) >= 2
    assert plan.assessment_checkpoints
    assert plan.learning_plan["assess_performance"].startswith("Assessment evidence")
    assert not hard_issues
    assert not hard_critiques


@pytest.mark.asyncio
async def test_staged_planner_adapts_to_weak_prerequisites_and_advanced_persona() -> None:
    weak = await planner_node({
        "raw_request": "Teach fractions",
        "class_info": {
            "grade": "Grade 5",
            "subject": "math",
            "student_count": 20,
            "proficiency_level": "beginner",
            "prior_knowledge_gaps": ["equivalent fractions"],
        },
        "kt_mastery": {"Fraction foundations": {"mastery": 0.2, "confidence": "high"}},
        "run_id": "run-weak",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "use_staged_planner": True,
    })
    advanced = await planner_node({
        "raw_request": "Teach fractions",
        "class_info": {
            "grade": "Grade 5",
            "subject": "math",
            "student_count": 20,
            "proficiency_level": "advanced",
        },
        "kt_mastery": {"Fraction foundations": {"mastery": 0.9, "confidence": "high"}},
        "run_id": "run-advanced",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "use_staged_planner": True,
    })

    weak_plan = LessonPlan.model_validate(weak["lesson_plan"])
    advanced_plan = LessonPlan.model_validate(advanced["lesson_plan"])

    assert any("reteach" in item.casefold() for item in weak_plan.prerequisite_knowledge)
    assert any(objective.bloom_level == "analyze" for objective in advanced_plan.learning_objectives)
    assert weak_plan.duration_minutes <= advanced_plan.duration_minutes


def test_lesson_validator_repairs_prerequisite_before_apply_ordering() -> None:
    invalid = LessonPlan.model_validate({
        "topic": "Fractions",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 45,
        "learning_objectives": [
            {"description": "Apply fractions", "bloom_level": "apply", "assessment_method": "Exit ticket"},
            {"description": "Remember fraction terms", "bloom_level": "remember", "assessment_method": "Warmup"},
        ],
        "prerequisite_knowledge": ["fraction terms"],
        "learning_plan": {
            "gain_attention": "Hook",
            "inform_objectives": "Objectives",
            "recall_prior": "Recall terms",
            "present_content": "Content",
            "provide_guidance": "Guidance",
            "elicit_performance": "Practice",
            "provide_feedback": "Feedback",
            "assess_performance": "Assess",
            "enhance_retention": "Retention",
        },
        "assessment_checkpoints": [
            {"type": "exit_ticket", "description": "Check apply fractions", "trigger": "lesson_end"},
        ],
    })

    repaired = LessonConsistencyValidator().repair(invalid)

    assert [objective.bloom_level for objective in repaired.learning_objectives] == ["remember", "apply"]
    assert not [
        issue
        for issue in LessonConsistencyValidator().validate(repaired)
        if issue.severity is LessonConsistencySeverity.HARD
    ]


@pytest.mark.asyncio
async def test_seed_mode_uses_staged_engine_without_drifting_seed_constraints() -> None:
    result = await planner_node({
        "raw_request": "Generate child lesson",
        "class_info": {"grade": "Grade 5", "subject": "math"},
        "run_id": "run-seed-staged",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "use_staged_planner": True,
        "seed": {
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
        },
    })

    plan = LessonPlan.model_validate(result["lesson_plan"])

    assert plan.duration_minutes == 45
    assert {objective.description for objective in plan.learning_objectives} == {"Students can apply fractions"}
    assert {objective.bloom_level for objective in plan.learning_objectives} == {"apply"}
    assert set(plan.prerequisite_knowledge) == {"Fraction equivalence"}
    assert plan.methodology is not None
    assert plan.methodology.tags == ["timed_quiz"]
