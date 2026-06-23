"""Pedagogical metrics — 7 binary checks for content quality.

All 7 metrics must pass for Layer 2 to succeed:
1. prompt_alignment — content matches the original request
2. factual_correctness — claims are verifiable
3. clarity — content is clear and unambiguous
4. contextual_relevance — content fits the lesson context
5. engagement — content is engaging for the target age group
6. harmful_content_avoidance — no harmful or inappropriate content
7. solution_accuracy — answers and solutions are correct
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The 7 required pedagogical metrics
REQUIRED_METRICS: list[str] = [
    "prompt_alignment",
    "factual_correctness",
    "clarity",
    "contextual_relevance",
    "engagement",
    "harmful_content_avoidance",
    "solution_accuracy",
]


@dataclass
class PedagogicalResult:
    """Result of pedagogical metrics check."""

    passed: bool
    metrics: dict[str, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def check_pedagogical_metrics(
    content: dict[str, Any],
    *,
    lesson_plan: dict[str, Any] | None = None,
    research_bundle: dict[str, Any] | None = None,
) -> PedagogicalResult:
    """Run all 7 binary pedagogical metrics against content.

    All 7 must pass for the check to succeed.

    Args:
        content: Artifact content to evaluate.
        lesson_plan: Original lesson plan for alignment checks.
        research_bundle: Research bundle for fact-checking.

    Returns:
        PedagogicalResult with per-metric pass/fail and issues.

    TODO: Implement each metric check.
    """
    # TODO: Implement 7 metric checks
    # Each returns True/False + optional issue description
    metrics = {metric: True for metric in REQUIRED_METRICS}
    all_passed = all(metrics.values())

    return PedagogicalResult(
        passed=all_passed,
        metrics=metrics,
        issues=[],
    )
