from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.slide_deck import (
    SlideDeckData,
    SlideDeckDisplayPreferences,
    resolve_slide_deck_display_preferences,
)


def _deck_without_display_preferences() -> dict[str, object]:
    """A minimal deck dict shaped like an artifact that predates ADR-043."""
    return {
        "deck_id": "deck-legacy",
        "title": "Legacy Deck",
        "locale": "en-US",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [
            {
                "slide_id": "slide-1",
                "title": "Intro",
                "layout": "title",
                "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
                "blocks": [
                    {"block_id": "block-1", "block_type": "heading", "body": "Intro"},
                ],
            }
        ],
        "accessibility": {
            "reading_level": "Grade 5",
            "language": "en",
        },
        "media_policy": {
            "default_tier": "packaged",
            "online_optional_allowed": False,
            "fallback_required": False,
        },
    }


def test_defaults_match_adr_043_production_safe_values() -> None:
    preferences = SlideDeckDisplayPreferences()

    assert preferences.surface == "presentation"
    assert preferences.print_layout == "paged"
    assert preferences.slides_per_page == 1
    assert preferences.chrome == "hidden"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("surface", "robot_mode"),
        ("print_layout", "scaled"),
        ("slides_per_page", 3),
        ("chrome", "loud"),
    ],
)
def test_strict_construction_rejects_invalid_options(
    field_name: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        SlideDeckDisplayPreferences(**{field_name: invalid_value})


def test_resolve_defaults_when_no_preferences_are_supplied() -> None:
    assert resolve_slide_deck_display_preferences(None) == SlideDeckDisplayPreferences()
    assert resolve_slide_deck_display_preferences({}) == SlideDeckDisplayPreferences()


def test_resolve_falls_back_field_by_field_on_invalid_options() -> None:
    resolved = resolve_slide_deck_display_preferences({
        "surface": "print",
        "print_layout": "sideways",  # invalid -> falls back to default
        "slides_per_page": 4,
        "chrome": "very_loud",  # invalid -> falls back to default
    })

    assert resolved.surface == "print"
    assert resolved.print_layout == "paged"
    assert resolved.slides_per_page == 4
    assert resolved.chrome == "hidden"


def test_resolve_accepts_only_valid_slides_per_page_values() -> None:
    for valid_value in (1, 2, 4, 6):
        resolved = resolve_slide_deck_display_preferences({"slides_per_page": valid_value})
        assert resolved.slides_per_page == valid_value
    assert resolve_slide_deck_display_preferences({"slides_per_page": 3}).slides_per_page == 1
    assert resolve_slide_deck_display_preferences({"slides_per_page": "2"}).slides_per_page == 1


def test_existing_deck_without_display_preferences_still_parses() -> None:
    deck = SlideDeckData(**_deck_without_display_preferences())

    assert deck.display_preferences is None
    # The render/export boundary resolves the missing field to safe defaults.
    effective = resolve_slide_deck_display_preferences(
        deck.display_preferences.model_dump() if deck.display_preferences else None
    )
    assert effective == SlideDeckDisplayPreferences()
