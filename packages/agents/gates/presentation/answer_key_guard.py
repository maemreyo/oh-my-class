"""Answer key leakage guard for student-facing artifacts."""
from __future__ import annotations

from typing import Any

from packages.quality.compliance_policy import check_artifact_answer_key_leakage


def check_answer_key_leakage(artifact: dict[str, Any]) -> dict[str, Any]:
    """Check that student-facing artifacts don't contain answer keys.

    Args:
        artifact: dict with 'type' and 'content' keys.

    Returns:
        {"passed": bool, "errors": list[str]}
    """
    result = check_artifact_answer_key_leakage(artifact)
    return {"passed": result["passed"], "errors": result["teacher_reasons"]}
