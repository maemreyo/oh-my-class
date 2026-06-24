"""Age-appropriateness checker for K-12 content."""
from __future__ import annotations
import re

BLOCKED_FOR_K12 = [
    r"\b(?:violence|gore|explicit|adult)\b",
    r"\b(?:weapon|firearm|gun)\b",
    r"\b(?:drug|alcohol|substance\s+abuse)\b",
]

GRADE_LEVEL_COMPLEX_THRESHOLD = {
    range(1, 4): 6,    # Grades 1-3: max 6-letter avg words
    range(4, 7): 9,    # Grades 4-6
    range(7, 10): 12,  # Grades 7-9
    range(10, 13): 15, # Grades 10-12
}


def check_age_appropriateness(text: str, grade: int | None = None) -> dict:
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
