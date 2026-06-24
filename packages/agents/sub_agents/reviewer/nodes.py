"""Reviewer Agent — LangGraph node function.

LLM-as-Judge with G-Eval scoring. Uses f.pro (different from generator)
to avoid self-review bias.
"""

from __future__ import annotations

from typing import Any

from packages.agents.sub_agents.reviewer.state import ReviewerState


async def reviewer_node(state: ReviewerState) -> dict[str, Any]:
    """Review artifacts using G-Eval criteria.

    Returns: {"quality_scores": {...}, "quality_passed": bool}
    """
    from packages.quality.layer4_judge.geval import GEvalScorer

    artifacts = state.get("artifacts") or []
    lesson_plan = state.get("lesson_plan")

    scorer = GEvalScorer()
    judge_output = await scorer.score(artifacts, lesson_plan=lesson_plan)

    return {
        "quality_scores": judge_output.model_dump(),
        "quality_passed": judge_output.passed,
    }
