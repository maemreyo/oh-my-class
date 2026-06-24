"""Layer 3: Full regeneration — clear all downstream state."""
from __future__ import annotations


def apply(state: dict, fail_count: int) -> dict:
    """Full regeneration: clear all downstream state, back to step_08."""
    return {
        "fail_count": fail_count,
        "healing_strategy": "replan",
        "artifacts": None,
        "review_results": None,
        "judge_score": None,
        "content_review_passed": None,
        "schema_valid": None,
        "healing_note": "Full regeneration triggered after 3 failed attempts",
    }
