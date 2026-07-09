from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.slide_deck import PedagogicalRole, SlideDeckData


def _slide(slide_id: str, **overrides: object) -> dict[str, object]:
    return {
        "slide_id": slide_id,
        "title": "A slide",
        "layout": "title",
        "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
        "blocks": [{"block_id": f"{slide_id}-block", "block_type": "heading", "body": "Hello"}],
        **overrides,
    }


def _deck(**slide_overrides: object) -> dict[str, object]:
    return {
        "deck_id": "deck-pacing",
        "title": "Pacing Test Deck",
        "locale": "en-US",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [_slide("slide-1", **slide_overrides)],
        "accessibility": {"reading_level": "Grade 5", "language": "en", "alt_text_required": True, "keyboard_navigation": True},
        "media_policy": {"default_tier": "packaged", "online_optional_allowed": False, "fallback_required": False},
    }


def test_pedagogical_role_taxonomy_matches_adr045_vocabulary() -> None:
    assert set(PedagogicalRole.__args__) == {
        "hook", "objective", "explain", "model", "guided_practice",
        "check_understanding", "independent_practice", "recap", "exit_ticket",
    }


def test_slide_pedagogical_role_defaults_to_none_and_is_separate_from_layout() -> None:
    deck = SlideDeckData.model_validate(_deck())

    assert deck.slides[0].pedagogical_role is None
    assert deck.slides[0].layout == "title"


def test_slide_accepts_a_typed_pedagogical_role_and_planned_duration() -> None:
    deck = SlideDeckData.model_validate(_deck(pedagogical_role="hook", planned_duration_minutes=3.5))

    assert deck.slides[0].pedagogical_role == "hook"
    assert deck.slides[0].planned_duration_minutes == 3.5


def test_slide_rejects_a_role_outside_the_taxonomy() -> None:
    with pytest.raises(ValidationError):
        SlideDeckData.model_validate(_deck(pedagogical_role="not_a_real_role"))


def test_slide_rejects_a_negative_planned_duration() -> None:
    with pytest.raises(ValidationError):
        SlideDeckData.model_validate(_deck(planned_duration_minutes=-1))


def test_deck_total_planned_duration_is_none_when_no_slide_has_one() -> None:
    deck = SlideDeckData.model_validate(_deck())

    assert deck.total_planned_duration_minutes is None


def test_deck_total_planned_duration_rolls_up_across_slides() -> None:
    payload = _deck()
    payload["slides"] = [
        _slide("slide-1", pedagogical_role="hook", planned_duration_minutes=2),
        _slide("slide-2", pedagogical_role="objective", planned_duration_minutes=3.5),
    ]
    deck = SlideDeckData.model_validate(payload)

    assert deck.total_planned_duration_minutes == 5.5
