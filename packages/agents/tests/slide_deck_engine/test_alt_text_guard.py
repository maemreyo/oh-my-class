from __future__ import annotations

import json
from typing import TYPE_CHECKING

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest

if TYPE_CHECKING:
    import pytest

# SDX-04 guard test: no media block in a generated deck may have empty or
# obviously-placeholder alt text. `_PLACEHOLDER_STRINGS` includes the exact
# generic fallback content_materialization.py used to produce for every
# title-slide image (`f"Visual model for {topic}."`) before SDX-04 wired the
# LLM-authored image_alt_text field in — the guard is proven to have teeth by
# feeding that exact old string through it below.
_PLACEHOLDER_STRINGS = (
    "image",
    "illustration",
    "hình ảnh",
    "hình ảnh minh họa",
    "visual model for equivalent fractions.",  # old generic fallback, lowercased
)


def _is_placeholder_alt_text(alt_text: str) -> bool:
    normalized = alt_text.strip().lower()
    return not normalized or normalized in _PLACEHOLDER_STRINGS


def _media_alt_texts(deck) -> list[str]:
    return [block.media.alt_text for slide in deck.slides for block in slide.blocks if block.media]


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-alt-text-guard",
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Explain why two fractions are equivalent."},
            ],
        },
        research_brief={
            "sources": [
                {"id": "src-fractions", "title": "Grade 5 Fractions Standard", "citation": "CCSS 5.NF.A"},
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


async def test_llm_authored_alt_text_is_descriptive_not_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({
            "image_alt_text": (
                "A pie chart split into eighths beside one split into quarters, "
                "showing four eighths shaded is the same amount as two quarters."
            ),
        })

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    alt_texts = _media_alt_texts(result.deck)
    assert alt_texts, "expected at least one media block"
    for alt_text in alt_texts:
        assert not _is_placeholder_alt_text(alt_text), alt_text


async def test_llm_failure_falls_back_to_generic_alt_text_not_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM-failure path: falls back to the deterministic generic string —
    never empty/broken, even though it isn't genuinely descriptive."""
    from packages.agents import llm

    async def raising_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        raise TimeoutError("simulated 9router timeout")

    monkeypatch.setattr(llm, "complete_json_chat", raising_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    alt_texts = _media_alt_texts(result.deck)
    assert alt_texts
    for alt_text in alt_texts:
        assert alt_text  # never empty
        assert 1 <= len(alt_text) <= 500  # schema constraint


def test_guard_has_teeth_the_old_generic_string_would_have_failed() -> None:
    """Regression-proof: the exact generic fallback SDX-04 replaced would be
    caught by this guard, so the guard isn't vacuously passing."""
    old_generic_alt_text = "Visual model for Equivalent fractions."
    assert _is_placeholder_alt_text(old_generic_alt_text)


def test_guard_rejects_empty_and_bare_generic_labels() -> None:
    for bad in ("", "   ", "image", "Illustration", "hình ảnh minh họa", "Hình Ảnh"):
        assert _is_placeholder_alt_text(bad), bad
