"""Roadmap Agent tools — book recommender and milestone calculator."""

from __future__ import annotations

from typing import Any

_BOOK_DB: dict[str, list[dict[str, str]]] = {
    "B1": [
        {"title": "Destination B1", "publisher": "Macmillan", "focus": "grammar + vocabulary"},  # noqa: E501
        {"title": "English Grammar in Use (Intermediate)", "publisher": "Cambridge", "focus": "grammar"},  # noqa: E501
        {"title": "Vocabulary in Use (Pre-Intermediate)", "publisher": "Cambridge", "focus": "vocabulary"},  # noqa: E501
    ],
    "B2": [
        {"title": "Destination B2", "publisher": "Macmillan", "focus": "grammar + vocabulary for HSA/IELTS"},  # noqa: E501
        {"title": "Advanced Grammar in Use", "publisher": "Cambridge", "focus": "grammar"},  # noqa: E501
        {"title": "Vocabulary in Use (Upper-Intermediate)", "publisher": "Cambridge", "focus": "vocabulary"},  # noqa: E501
        {"title": "Common Mistakes at B2", "publisher": "Cambridge", "focus": "error correction"},  # noqa: E501
    ],
    "C1": [
        {"title": "Destination C1 & C2", "publisher": "Macmillan", "focus": "advanced grammar + vocabulary"},  # noqa: E501
        {"title": "English Collocations in Use (Advanced)", "publisher": "Cambridge", "focus": "collocations"},  # noqa: E501
        {"title": "Academic Vocabulary in Use", "publisher": "Cambridge", "focus": "academic vocabulary"},  # noqa: E501
    ],
}

_WEAK_SKILL_SUPPLEMENTS: dict[str, list[dict[str, str]]] = {
    "vocabulary": [
        {"title": "Word Power Made Easy", "publisher": "Pocket Books", "focus": "word building"},
    ],
    "collocation": [
        {"title": "Oxford Collocations Dictionary", "publisher": "Oxford", "focus": "collocations"},
    ],
    "reading_comprehension": [
        {"title": "Reading Explorer", "publisher": "National Geographic", "focus": "reading skills"},  # noqa: E501
    ],
    "grammar": [
        {"title": "Murphy's English Grammar", "publisher": "Cambridge", "focus": "reference grammar"},  # noqa: E501
    ],
}


def book_recommender(level: str, weak_skills: list[str]) -> dict[str, Any]:
    """Recommend textbooks based on CEFR level and weak skills.

    Args:
        level: CEFR level — "B1", "B2", or "C1".
        weak_skills: List of weak skill areas (e.g. ["vocabulary", "grammar"]).

    Returns:
        Dict with "core_books" and "supplement_books" lists.
    """
    core = _BOOK_DB.get(level, _BOOK_DB["B2"])
    supplements: list[dict[str, str]] = []
    for skill in (weak_skills or []):
        supplements.extend(_WEAK_SKILL_SUPPLEMENTS.get(skill, []))

    seen: set[str] = set()
    unique_supplements: list[dict[str, str]] = []
    for book in supplements:
        key = book["title"]
        if key not in seen:
            seen.add(key)
            unique_supplements.append(book)

    return {"level": level, "core_books": core, "supplement_books": unique_supplements}


def milestone_calculator(
    target_score: int,
    current_error_rate: float,
    months: int,
) -> list[dict[str, Any]]:
    """Calculate monthly score milestones toward a target exam score.

    Uses a linear interpolation model with front-loading (faster early progress).

    Args:
        target_score: Target exam score (e.g. 40 for HSA).
        current_error_rate: Current overall error rate (0.0–1.0).
        months: Study duration in months.

    Returns:
        List of {"month": int, "target_score": int, "focus": str} dicts.
    """
    estimated_current = int(target_score * (1.0 - current_error_rate))
    score_gap = max(0, target_score - estimated_current)

    focus_labels = [
        "Foundation — core grammar + high-frequency vocabulary",
        "Consolidation — weak areas + collocations",
        "Practice — past papers + timed exercises",
        "Refinement — nuance + advanced patterns",
        "Simulation — full mock tests + error analysis",
        "Final polish — targeted revision + exam strategy",
    ]

    milestones = []
    for m in range(1, months + 1):
        progress_ratio = m / months
        front_loaded = progress_ratio ** 0.7
        monthly_score = estimated_current + int(score_gap * front_loaded)
        focus_idx = min(m - 1, len(focus_labels) - 1)
        milestones.append({
            "month": m,
            "target_score": min(monthly_score, target_score),
            "focus": focus_labels[focus_idx],
        })

    return milestones
