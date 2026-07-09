from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.slide_deck import (
    SLIDE_DECK_DIFFERENTIATION_LEVELS,
    SlideDeckData,
    SlideDeckDifferentiationNote,
)
from common.contracts.tests.test_slide_deck import _valid_deck


def test_differentiation_note_represents_scaffold_and_stretch_separately() -> None:
    scaffold = SlideDeckDifferentiationNote(level="scaffold", guidance="Provide a labeled fraction bar.")
    stretch = SlideDeckDifferentiationNote(level="stretch", guidance="Ask for an equivalent fraction with a prime denominator.")

    assert scaffold.level == "scaffold"
    assert stretch.level == "stretch"
    assert scaffold.guidance != stretch.guidance
    assert set(SLIDE_DECK_DIFFERENTIATION_LEVELS) == {"scaffold", "stretch"}


def test_differentiation_note_is_a_distinct_model_from_answer_keys() -> None:
    # AC: "separately from answer keys" -- this is its own field/model, not
    # merged into `SlideDeckTeacherOnly.answer_key_notes`.
    assert "answer" not in " ".join(SlideDeckDifferentiationNote.model_fields).lower()


def test_differentiation_note_rejects_empty_level_or_guidance() -> None:
    with pytest.raises(ValidationError):
        SlideDeckDifferentiationNote(level="", guidance="Some guidance.")

    with pytest.raises(ValidationError):
        SlideDeckDifferentiationNote(level="scaffold", guidance="")


def test_differentiation_note_level_is_not_restricted_to_scaffold_and_stretch() -> None:
    # Leaves room for future group/level variants without a schema change:
    # `level` is a free string, not a `Literal["scaffold", "stretch"]`.
    future_variant = SlideDeckDifferentiationNote(level="esl_support", guidance="Pre-teach 'equivalent' and 'denominator'.")

    assert future_variant.level == "esl_support"


def test_slide_can_carry_scaffold_and_stretch_guidance_distinct_from_teacher_notes() -> None:
    payload = _valid_deck()
    payload["slides"][0]["differentiation_guidance"] = [
        {"level": "scaffold", "guidance": "Provide a labeled fraction bar."},
        {"level": "stretch", "guidance": "Ask for an equivalent fraction with a prime denominator."},
    ]

    deck = SlideDeckData.model_validate(payload)

    guidance = deck.slides[0].differentiation_guidance
    assert [note.level for note in guidance] == ["scaffold", "stretch"]
    assert deck.slides[0].teacher_notes is not None
    assert guidance[0].guidance not in deck.slides[0].teacher_notes.answer_key_notes


def test_deck_without_differentiation_guidance_still_validates() -> None:
    # Foundation default: existing decks with no differentiation_guidance
    # field at all keep validating unchanged.
    deck = SlideDeckData.model_validate(_valid_deck())

    assert deck.slides[0].differentiation_guidance == []


def test_differentiation_guidance_supports_more_than_two_levels_without_a_breaking_change() -> None:
    # AC: "leaves room for future group/level variants without implementing
    # them in this slice" -- a third (or Nth) level is just another list item.
    payload = _valid_deck()
    payload["slides"][0]["differentiation_guidance"] = [
        {"level": "scaffold", "guidance": "Provide a labeled fraction bar."},
        {"level": "stretch", "guidance": "Ask for an equivalent fraction with a prime denominator."},
        {"level": "advanced_group_a", "guidance": "Assign the extension worksheet."},
    ]

    deck = SlideDeckData.model_validate(payload)

    assert [note.level for note in deck.slides[0].differentiation_guidance] == [
        "scaffold", "stretch", "advanced_group_a",
    ]
