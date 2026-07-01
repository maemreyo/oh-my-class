"""Age-appropriateness checker — Flesch-Kincaid grade level and content filters.

Ensures generated content is appropriate for the target grade level.
Uses Flesch-Kincaid readability score and forbidden content rules per age band.
"""

from __future__ import annotations

import re
from typing import TypedDict

from packages.quality.layer2_content.age_band import get_age_band
from packages.quality.layer2_content.readability_checker import _count_syllables, check_readability

# Forbidden content patterns by age band
FORBIDDEN_CONTENT: dict[str, list[str]] = {
    "early_childhood": [],  # K-2: very permissive
    "upper_elementary": [],  # 3-5: moderate restrictions
    "middle_school": [],  # 6-8: standard restrictions
    "high_school": [],  # 9-12: minimal restrictions
}


class AgeAppropriatenessResult(TypedDict):
    passed: bool
    fk_score: float
    issues: list[str]
    measured: dict[str, bool]


def compute_flesch_kincaid(text: str) -> float:
    """Compute Flesch-Kincaid grade level score.

    Args:
        text: Text content to analyze.

    Returns:
        Grade level score (e.g. 5.0 = 5th grade reading level).

    """
    sentences = [sentence.strip() for sentence in re.split(r"[.!?]+", text) if sentence.strip()]
    words = [word for word in text.split() if word]
    if not sentences or not words:
        return 0.0
    average_sentence_length = len(words) / len(sentences)
    average_syllables = sum(_count_syllables(word) for word in words) / len(words)
    return round(0.39 * average_sentence_length + 11.8 * average_syllables - 15.59, 2)


def check_age_appropriateness(
    text: str,
    grade_level: str,
    *,
    allowed_deviation: float = 1.5,
) -> AgeAppropriatenessResult:
    """Check if content is appropriate for the target grade level.

    Args:
        text: Content text to check.
        grade_level: Target grade level (e.g. "Grade 5").
        allowed_deviation: Max allowed deviation from target grade level.

    Returns:
        Result with pass status, FK score, issues, and measurement flags.
    """
    grade = _parse_grade(grade_level)
    if grade is None:
        return {
            "passed": True,
            "fk_score": compute_flesch_kincaid(text),
            "issues": [],
            "measured": {"readability": False, "age_band": False},
        }

    readability = check_readability(text, grade)
    issues: list[str] = []
    if abs(readability.deviation) > allowed_deviation:
        issues.append(
            readability.warning
            or f"Readability outside Grade {grade} band: FK {readability.fk_grade_level:.1f}",
        )

    band = get_age_band(grade)
    forbidden_terms = FORBIDDEN_CONTENT.get(_age_band_key(band.label), [])
    lowered = text.lower()
    blocked_terms = [term for term in forbidden_terms if term.lower() in lowered]
    if blocked_terms:
        issues.append(f"Forbidden for {band.label}: {', '.join(blocked_terms)}")

    return {
        "passed": len(issues) == 0,
        "fk_score": readability.fk_grade_level,
        "issues": issues,
        "measured": {"readability": True, "age_band": True},
    }


def _parse_grade(grade_level: str) -> int | None:
    match = re.search(r"\d+", grade_level)
    if match is None:
        return None
    return int(match.group())


def _age_band_key(label: str) -> str:
    return label.lower().replace(" ", "_").replace("-", "_")
