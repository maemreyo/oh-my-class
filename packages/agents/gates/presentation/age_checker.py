"""Age-appropriateness checker for K-12 content."""
from __future__ import annotations

import re
from typing import Any

BLOCKED_FOR_K12 = [
    r"\b(?:violence|gore|explicit|adult)\b",
    r"\b(?:weapon|firearm|gun)\b",
    r"\b(?:drug|alcohol|substance\s+abuse)\b",
]


def check_age_appropriateness(text: str, grade: int | None = None) -> dict[str, Any]:
    """Check if text is age-appropriate for the given grade level.

    Returns:
        {"passed": bool, "errors": list[str], "warnings": list[str]}
    """
    errors = []
    warnings = []

    for pattern in BLOCKED_FOR_K12:
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(f"Content blocked: matches pattern '{pattern}'")

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}
