from __future__ import annotations

import json
from typing import TYPE_CHECKING

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest

if TYPE_CHECKING:
    import pytest

# SDE-01: ContentMaterializer's real, schema-bound llm_client call. The autouse
# `_stub_slide_deck_wording_llm` fixture (conftest.py in this package) already
# covers the "LLM returns nothing usable" path (see test_engine.py); these tests
# cover the LLM-succeeds and LLM-fails-in-various-ways paths specifically.

_WORDING_FIELDS = (
    "vocabulary_body",
    "vocabulary_practice_body",
    "example_body",
    "sentence_stem",
    "check_prompt",
    "practice_correct_option",
    "practice_distractor_a",
    "practice_distractor_b",
    "teacher_rationale",
    "exit_prompt",
)


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-content-materialization-llm",
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


def _interactions(slide) -> list:
    return slide.interactions or []


def _deck_text(deck) -> str:
    bodies = [block.body for slide in deck.slides for block in slide.blocks]
    prompts = [interaction.prompt for slide in deck.slides for interaction in _interactions(slide)]
    options = [
        option.label
        for slide in deck.slides
        for interaction in _interactions(slide)
        for option in (interaction.options or [])
    ]
    rationales = [
        interaction.teacher_only.rationale
        for slide in deck.slides
        for interaction in _interactions(slide)
        if interaction.teacher_only
    ]
    return " ".join([*bodies, *prompts, *options, *rationales])


async def test_llm_authored_wording_reaches_the_deck_and_counts_as_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.agents import llm

    wording = {field: f"LLM_WORDING_MARKER_{field}" for field in _WORDING_FIELDS}

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps(wording)

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    assert result.trace.llm_calls == 1
    assert result.trace.model_cost_metadata == {
        "llm_calls": 1,
        "estimated_cost_usd": 0.0,
        "provider": "llm_client",
    }
    deck_text = _deck_text(result.deck)
    for field in _WORDING_FIELDS:
        assert f"LLM_WORDING_MARKER_{field}" in deck_text
    # LLM-authored content still clears the existing objective-coverage and
    # teacher-only-separation validators — no unvalidated LLM text reaches a
    # slide unchecked. (Registry-membership scoring is intentionally not
    # asserted here: LAYOUT_REGISTRY/BLOCK_REGISTRY are pre-existing,
    # out-of-scope-for-SDE-01 gaps — see the spawned follow-up task.)
    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.teacher_only_separation_score == 1.0


async def test_llm_timeout_falls_back_to_deterministic_wording_not_a_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.agents import llm

    async def raising_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        raise TimeoutError("simulated 9router timeout")

    monkeypatch.setattr(llm, "complete_json_chat", raising_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    assert result.trace.llm_calls == 0
    assert result.trace.model_cost_metadata == {
        "llm_calls": 0,
        "estimated_cost_usd": 0.0,
        "provider": "none",
    }
    # Falls back to the engine's real, curated per-topic wording (not an empty
    # placeholder) — the deck is still fully valid and clears the same checks.
    vocabulary_slide = next(slide for slide in result.deck.slides if slide.slide_id == "slide-vocabulary")
    assert vocabulary_slide.blocks[0].body
    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.teacher_only_separation_score == 1.0


async def test_llm_invalid_json_falls_back_to_deterministic_wording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.agents import llm

    async def malformed_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return "not json at all"

    monkeypatch.setattr(llm, "complete_json_chat", malformed_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    assert result.trace.llm_calls == 0
    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.teacher_only_separation_score == 1.0


async def test_llm_response_that_breaks_deck_schema_discards_the_whole_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized field fails SlideDeckData validation post-assembly — treated
    the same as any other invalid-schema failure: the whole call is discarded
    and the deck falls back to fully deterministic wording (see the
    `ponytail:` all-or-nothing note in content_materialization.py).
    """
    from packages.agents import llm

    oversized_wording = {field: f"LLM_WORDING_MARKER_{field}" for field in _WORDING_FIELDS}
    oversized_wording["vocabulary_body"] = "x" * 5000  # exceeds SlideDeckBlock.body's max_length=2000

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps(oversized_wording)

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await SlideDeckEngine().generate(_request())

    assert result.trace.llm_calls == 0
    deck_text = _deck_text(result.deck)
    assert "LLM_WORDING_MARKER" not in deck_text
    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.teacher_only_separation_score == 1.0
