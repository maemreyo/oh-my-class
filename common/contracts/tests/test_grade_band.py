from __future__ import annotations

import pytest

from common.contracts.grade_band import GradeBand, grade_band_for_grade, grade_band_for_label


@pytest.mark.parametrize(("grade", "expected"), [
    (0, GradeBand.K_2),
    (2, GradeBand.K_2),
    (3, GradeBand.GRADES_3_5),
    (5, GradeBand.GRADES_3_5),
    (6, GradeBand.GRADES_6_8),
    (8, GradeBand.GRADES_6_8),
    (9, GradeBand.GRADES_9_12),
    (12, GradeBand.GRADES_9_12),
])
def test_grade_band_for_grade_boundaries(grade: int, expected: GradeBand) -> None:
    assert grade_band_for_grade(grade) is expected


@pytest.mark.parametrize(("label", "expected"), [
    ("Grade 5", GradeBand.GRADES_3_5),
    ("grade 10", GradeBand.GRADES_9_12),
    ("K", GradeBand.K_2),
    ("Kindergarten", GradeBand.K_2),
    ("Grade 1", GradeBand.K_2),
])
def test_grade_band_for_label_parses_common_formats(label: str, expected: GradeBand) -> None:
    assert grade_band_for_label(label) is expected


def test_grade_band_for_label_returns_none_when_unparseable() -> None:
    assert grade_band_for_label("Unknown") is None
