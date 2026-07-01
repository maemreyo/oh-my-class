from __future__ import annotations

from packages.quality.layer2_content.age_check import check_age_appropriateness


def test_age_check_flags_readability_above_grade_band() -> None:
    result = check_age_appropriateness(
        "Photosynthesis requires conceptualization of chlorophyll-mediated biochemical conversion. "
        "Learners synthesize evidence about molecular transformation and energetic transfer.",
        "Grade 1",
    )

    assert result["passed"] is False
    assert result["measured"]["readability"] is True
    assert result["fk_score"] > 0.0
    assert result["issues"]


def test_age_check_reports_unmeasured_for_unknown_grade() -> None:
    result = check_age_appropriateness("Simple classroom text.", "primary")

    assert result["passed"] is True
    assert result["measured"]["readability"] is False
    assert result["issues"] == []
