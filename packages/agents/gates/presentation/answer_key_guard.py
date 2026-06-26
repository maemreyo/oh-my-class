"""Answer key leakage guard for student-facing artifacts."""
from __future__ import annotations

import re
from typing import Any

ANSWER_LEAK_PATTERNS = [
    r"answer\s*key",
    r"correct\s+answer[s]?\s*:",
    r"solution[s]?\s*:",
    r"\banswer[s]?\s*:\s*[A-D]\b",
]

STUDENT_ARTIFACT_TYPES = {
    "activity_sheet",
    "drill",
    "quiz",
    "recap",
    "student_handout",
    "worksheet",
}


def _collect_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            if key in {"answer", "answer_key", "correct_answer", "correctAnswer"}:
                parts.append(f"Answer: {item}")
            elif key in {
                "components",
                "content",
                "explain",
                "explanation",
                "questions",
                "rationale",
                "sections",
                "text",
            }:
                parts.extend(_collect_text(item))
        return parts
    if isinstance(value, list):
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_text(item))
        return collected
    return []


def check_answer_key_leakage(artifact: dict[str, Any]) -> dict[str, Any]:
    """Check that student-facing artifacts don't contain answer keys.

    Args:
        artifact: dict with 'type' and 'content' keys.

    Returns:
        {"passed": bool, "errors": list[str]}
    """
    artifact_type = str(artifact.get("artifact_type", artifact.get("type", ""))).lower()
    if artifact_type not in STUDENT_ARTIFACT_TYPES:
        return {"passed": True, "errors": []}

    content = "\n".join(_collect_text(artifact))
    errors = []
    for pattern in ANSWER_LEAK_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Answer key leakage detected in {artifact_type}: matches '{pattern}'")

    return {"passed": len(errors) == 0, "errors": errors}
