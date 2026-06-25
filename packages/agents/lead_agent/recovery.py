"""D3 semantic recovery — builds targeted guidance for the Lead Agent after low review scores.

Graph enforces structural retry limits (max_revisions).
This module handles the semantic side: *what* to fix and *how*.
"""

from __future__ import annotations

from typing import Any


def build_recovery_context(review_results: dict[str, Any], revision_count: int) -> str:
    """Build semantic recovery guidance for the Lead Agent after a low review score.

    Args:
        review_results: Output from run_reviewer — overall_score, feedback, per_artifact.
        revision_count: How many revisions have been attempted so far.

    Returns:
        Markdown string injected into the Lead Agent's system messages on retry.
    """
    overall_score = review_results.get("overall_score", 0)
    feedback = review_results.get("feedback", "")
    per_artifact = review_results.get("per_artifact", {})

    weak_artifacts = [
        artifact_type
        for artifact_type, scores in per_artifact.items()
        if scores.get("overall", 10) < 7.0
    ]

    lines = [
        f"## Recovery Context (Revision {revision_count})",
        f"Overall score: {overall_score:.1f}/10 — below threshold.",
    ]

    if feedback:
        lines += ["", "### Reviewer Feedback", feedback]

    if weak_artifacts:
        lines += ["", f"### Weak artifacts: {', '.join(weak_artifacts)}"]
        for artifact_type in weak_artifacts:
            scores = per_artifact[artifact_type]
            lines.append(f"- **{artifact_type}**: {scores}")

    lines += [
        "",
        "### Your Task",
        "Regenerate ONLY the weak artifacts with targeted improvements.",
        "Address the specific feedback above. Do not regenerate passing artifacts.",
    ]

    return "\n".join(lines)
