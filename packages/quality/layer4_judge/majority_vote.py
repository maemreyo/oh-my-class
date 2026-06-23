"""Majority vote — aggregates results from 3 independent judge calls.

Uses majority voting to determine the final score and pass/fail status.
Reduces individual judge bias and improves reliability.
"""

from __future__ import annotations

from common.contracts.judge_output import JudgeOutput, LayerScore


def majority_vote(
    judge_outputs: list[JudgeOutput],
    *,
    pass_threshold: float = 7.0,
) -> JudgeOutput:
    """Aggregate multiple judge outputs via majority voting.

    For each layer, averages scores across all judges.
    For pass/fail, requires ≥2/3 of judges to pass AND avg_score >= threshold.
    For critical issues, unions all critical issues from judges.

    Args:
        judge_outputs: List of JudgeOutput from independent judges (should be 3).
        pass_threshold: Minimum overall score to pass.

    Returns:
        Aggregated JudgeOutput representing the consensus.

    Raises:
        ValueError: If fewer than 2 judge outputs are provided.
    """
    if len(judge_outputs) < 2:
        raise ValueError("Majority vote requires at least 2 judge outputs")

    total = len(judge_outputs)

    # Average overall score
    avg_overall = sum(j.overall_score for j in judge_outputs) / total

    # Average layer scores
    layer_names = ["format_compliance", "content_quality", "presentation"]
    layer_scores = []
    for layer_name in layer_names:
        layer_vals = []
        weight = 0.0
        for j in judge_outputs:
            for ls in j.layer_scores:
                if ls.layer == layer_name:
                    layer_vals.append(ls.score)
                    weight = ls.weight
        if layer_vals:
            layer_scores.append(
                LayerScore(
                    layer=layer_name,
                    score=sum(layer_vals) / len(layer_vals),
                    weight=weight,
                    issues=[],
                )
            )

    # Union critical issues (deduplicated)
    seen: set[str] = set()
    critical_issues: list[str] = []
    for j in judge_outputs:
        for issue in j.critical_issues:
            if issue not in seen:
                seen.add(issue)
                critical_issues.append(issue)

    # Majority pass: ≥2/3 judges AND score >= threshold AND no critical issues
    pass_count = sum(1 for j in judge_outputs if j.passed)
    passed = (
        pass_count >= total * 2 / 3
        and avg_overall >= pass_threshold
        and not critical_issues
    )

    return JudgeOutput(
        overall_score=avg_overall,
        layer_scores=layer_scores,
        critical_issues=critical_issues,
        passed=passed,
        rationale=judge_outputs[0].rationale,
    )
