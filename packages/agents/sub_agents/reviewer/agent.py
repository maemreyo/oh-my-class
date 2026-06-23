"""Reviewer Agent — node implementation.

LLM-as-Judge with 3-layer G-Eval scoring:
- Format compliance (15%): DOCTYPE, no CDN, brand strings, responsive
- Content quality (55%): accuracy, completeness, relevance, reasoning
- Presentation (30%): readability, engagement, accessibility

Pass threshold: overall_score >= 7.0 AND no critical issues.
Majority vote: 3 independent judge calls.

Bias mitigations:
- Rationale written before score (think-before-score)
- 3 independent judge calls → majority vote
- Generator model ≠ judge model
- Explicit guard: "Do not rate longer answers higher"

Uses content-fusion via 9Router combo: f.pro (fusion: parallel providers + judge)
Different model from generator for bias mitigation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def quality_review(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Reviewer Agent.

    Takes generated artifacts and produces quality scores via G-Eval.
    Runs 3 independent judge calls and takes majority vote.

    Args:
        state: Current pipeline state with artifacts and lesson_plan.

    Returns:
        Partial state update containing 'quality_scores' and 'quality_passed'.

    Output contract:
        JudgeOutput with overall_score, layer_scores, critical_issues,
        passed flag, and rationale.
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
