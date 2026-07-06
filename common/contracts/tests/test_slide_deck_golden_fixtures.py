from __future__ import annotations

import json
from pathlib import Path

from common.contracts.slide_deck import SlideDeckData


FIXTURE_DIR = Path(__file__).parents[2] / ".." / ".scratch" / "slide-deck-engine" / "fixtures" / "golden"


def test_slide_deck_golden_fixtures_parse_against_contract() -> None:
    fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))

    assert {path.name for path in fixture_paths} == {
        "answer-leak-regression-deck.json",
        "interaction-deck.json",
        "media-heavy-deck.json",
        "simple-lesson-deck.json",
        "teacher-notes-deck.json",
    }

    decks = [SlideDeckData(**json.loads(path.read_text(encoding="utf-8"))) for path in fixture_paths]

    assert {deck.deck_id for deck in decks} == {
        "golden-answer-leak-regression",
        "golden-interaction",
        "golden-media-heavy",
        "golden-simple-lesson",
        "golden-teacher-notes",
    }
    assert all(deck.surfaces.student.mode == "presentation" for deck in decks)
    assert all(deck.surfaces.teacher.mode == "teacher_guide" for deck in decks)
    assert all(deck.surfaces.print.mode == "print" for deck in decks)
