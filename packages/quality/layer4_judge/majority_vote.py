"""Majority vote — aggregates results from 3 independent judge calls.

Uses majority voting to determine the final score and pass/fail status.
Reduces individual judge bias and improves reliability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.contracts.judge_output import JudgeOutput


def majority_vote(
    judge_outputs: list[JudgeOutput],
    *,
    pass_threshold: float = 7.0,
) -> JudgeOutput:
    """Aggregate multiple judge outputs via majority voting.

    For each layer, takes the median score across judges.
    For pass/fail, requires majority (≥2/3) to pass.
    For critical issues, union all critical issues from judges.

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

    # TODO: Implement majority vote aggregation:
    # 1. Collect scores per layer across all judges
    # 2. Compute median score per layer
    # 3. Compute weighted overall score from median layer scores
    # 4. Majority pass/fail: ≥ceil(n/2) judges must have passed
    # 5. Union of critical issues
    # 6. Combine rationales

    # Placeholder: return first judge output
    return judge_outputs[0]
