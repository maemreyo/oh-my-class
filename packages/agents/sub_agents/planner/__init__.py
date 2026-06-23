"""Planner Agent — backward design (UbD) lesson planning.

Delegates to deepseek-v4-flash via LiteLLM.
Output: LessonPlan JSON (see common.contracts.lesson_plan).
"""

from packages.agents.sub_agents.planner.agent import design_lesson_plan

__all__ = ["design_lesson_plan"]
