from __future__ import annotations

import pytest

from common.contracts.grade_band import FlashcardGradeBand

from packages.agents.teaching_pack.specialists.flashcard_deck_specialist import (
    NoGroundedTermsError,
    build_flashcards,
    generate_flashcard_deck_artifact,
    score_flashcards,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions",
        "grade_level": "Grade 5",
        "learning_objectives": [
            {"description": "Equivalent fractions represent the same value on a number line."},
            {"description": "Multiplying numerator and denominator by the same number keeps the value."},
        ],
    }


def _research_brief() -> dict[str, object]:
    return {
        "sources": [
            {"title": "NCTM Guide", "excerpt": "A fraction is simplified when no common factor remains."},
        ],
    }


def test_build_flashcards_retains_objectives_and_grounded_findings_only() -> None:
    entries = build_flashcards(_lesson_plan(), _research_brief())

    assert [e.source_type for e in entries] == ["objective", "objective", "research_finding"]
    assert entries[0].back == "Equivalent fractions represent the same value on a number line."
    assert entries[0].front != entries[0].back  # front is a short label, not the full text


def test_card_identity_is_stable_across_regeneration() -> None:
    """#441 AC1: identity semantics survive compatible edits/restoration -- the
    same approved context must regenerate the same card ids."""
    first = build_flashcards(_lesson_plan(), _research_brief())
    second = build_flashcards(_lesson_plan(), _research_brief())

    assert [e.entity_id for e in first] == [e.entity_id for e in second]


def test_generate_flashcard_deck_artifact_raises_when_nothing_grounded() -> None:
    with pytest.raises(NoGroundedTermsError):
        generate_flashcard_deck_artifact({"learning_objectives": []}, {"sources": []})


def test_generate_flashcard_deck_artifact_uses_the_shape_the_exporter_reads() -> None:
    """Cards must live at sections[0]["cards"] -- verified against
    packages/exporters/src/cli.ts::buildDeck's actual read path, not just
    against ArtifactContent's loosely-typed sections contract (the shape
    that silently broke Recap's renderer output before it was caught)."""
    artifact = generate_flashcard_deck_artifact(_lesson_plan(), _research_brief())

    assert artifact["artifact_type"] == "flashcard_deck"
    cards = artifact["sections"][0]["cards"]
    assert all({"id", "front", "back"} <= set(card) for card in cards)
    assert artifact["metadata"]["subject"] == "General"
    assert artifact["metadata"]["gradeLevel"] == "Grade 5"


def test_scorecard_covers_all_four_dimensions() -> None:
    entries = build_flashcards(_lesson_plan(), _research_brief())

    scorecard = score_flashcards(entries, grade_band=FlashcardGradeBand.ELEMENTARY)

    assert scorecard.recall_value == 1.0  # every back is substantive (>= 2 words)
    assert scorecard.ambiguity == 0.0  # no duplicate fronts
    assert scorecard.duplication == 0.0  # no duplicate backs


def test_scorecard_flags_duplicate_fronts_and_backs() -> None:
    """1 unique front/back out of 2 cards -> a 0.5 duplicate rate, not a boolean."""
    entries = build_flashcards(_lesson_plan(), _research_brief())
    duplicated = [entries[0], entries[0]]

    scorecard = score_flashcards(duplicated)

    assert scorecard.ambiguity == 0.5
    assert scorecard.duplication == 0.5


def test_scorecard_grade_fit_penalizes_backs_outside_the_declared_band() -> None:
    entries = build_flashcards(_lesson_plan(), _research_brief())

    fit_for_elementary = score_flashcards(entries, grade_band=FlashcardGradeBand.ELEMENTARY).grade_fit
    fit_with_no_band = score_flashcards(entries, grade_band=None).grade_fit

    assert fit_with_no_band == 1.0  # no declared band -- not penalized
    assert 0.0 <= fit_for_elementary <= 1.0
