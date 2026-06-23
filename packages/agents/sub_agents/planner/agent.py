"""Planner Agent — node implementation.

Generates structured lesson plans using backward design (UbD) principles
and Gagné's 9-event instruction model. Output validated against
LessonPlan Pydantic schema.

Uses deepseek-v4-flash via 9Router combo: f.light (fast free tier)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def design_lesson_plan(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Planner Agent.

    Takes the teacher's raw request and class info, produces a structured
    LessonPlan JSON conforming to common.contracts.lesson_plan.LessonPlan.

    Args:
        state: Current pipeline state with raw_request and class_info.

    Returns:
        Partial state update containing 'lesson_plan' dict.

    Output contract:
        LessonPlan with topic, grade_level, subject, duration_minutes,
        learning_objectives (≥2 Bloom levels), prerequisite_knowledge,
        learning_plan (Gagné 9-event), assessment_checkpoints.
    """
    # TODO: Implement with LangGraph agent
    # 1. Format prompt from state
    # 2. Call LLM via LiteLLM (deepseek-v4-flash)
    # 3. Parse response into LessonPlan schema
    # 4. Validate via Pydantic (common.contracts.lesson_plan.LessonPlan)
    # 5. Return {"lesson_plan": plan.model_dump()}
    raise NotImplementedError("design_lesson_plan() stub — implement with Planner agent")
