from __future__ import annotations

from pathlib import Path

import pytest

from common.contracts.grade_band import (
    FlashcardGradeBand,
    GradeBand,
    StrategyKnowledgeGradeBand,
    flashcard_grade_band,
    grade_band_for_grade,
    grade_band_for_label,
    strategy_knowledge_grade_band,
)


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


@pytest.mark.parametrize("label", ["Grade -1", "Grade 13", "Lớp 13"])
def test_grade_band_for_label_rejects_out_of_range_labels(label: str) -> None:
    assert grade_band_for_label(label) is None


@pytest.mark.parametrize(("grade_band", "legacy"), [
    (GradeBand.K_2, None),
    (GradeBand.GRADES_3_5, StrategyKnowledgeGradeBand.GRADES_4_6),
    (GradeBand.GRADES_6_8, StrategyKnowledgeGradeBand.GRADES_7_9),
    (GradeBand.GRADES_9_12, StrategyKnowledgeGradeBand.GRADES_10_12),
])
def test_strategy_adapter_does_not_invent_unsupported_k2_knowledge(
    grade_band: GradeBand, legacy: StrategyKnowledgeGradeBand | None,
) -> None:
    assert strategy_knowledge_grade_band(grade_band) is legacy


@pytest.mark.parametrize(("grade_band", "legacy"), [
    (GradeBand.K_2, FlashcardGradeBand.ELEMENTARY),
    (GradeBand.GRADES_3_5, FlashcardGradeBand.ELEMENTARY),
    (GradeBand.GRADES_6_8, FlashcardGradeBand.MIDDLE),
    (GradeBand.GRADES_9_12, FlashcardGradeBand.HIGH),
])
def test_flashcard_adapter_maps_every_canonical_band(
    grade_band: GradeBand, legacy: FlashcardGradeBand,
) -> None:
    assert flashcard_grade_band(grade_band) is legacy


def test_legacy_grade_taxonomy_literals_are_confined_to_the_adapter() -> None:
    root = Path(__file__).resolve().parents[3]
    legacy_literals = (
        '"grade_4_6"',
        '"grade_7_9"',
        '"grade_10_12"',
        '"elementary"',
        '"middle"',
    )
    permitted = root / "common" / "contracts" / "grade_band.py"
    sources = [
        *sorted((root / "common").rglob("*.py")),
        *sorted((root / "packages").rglob("*.py")),
        *sorted((root / "services").rglob("*.py")),
    ]
    offenders = [
        source.relative_to(root).as_posix()
        for source in sources
        if "/tests/" not in source.as_posix()
        and source != permitted
        and any(literal in source.read_text(encoding="utf-8") for literal in legacy_literals)
    ]

    assert offenders == []
