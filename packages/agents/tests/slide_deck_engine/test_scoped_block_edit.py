from __future__ import annotations

import pytest

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.scoped_block_edit import (
    SlideDeckBlockEditInvalidError,
    SlideDeckBlockNotFoundError,
    apply_scoped_slide_deck_block_edit,
    slide_deck_block_edit_event,
)

# SDE-04: the single business function shared by the gate-resume path
# (packages/agents/teaching_pack/scoped_regeneration.py) and the standalone
# snapshot-edit endpoint (services/gateway/routers/teaching_pack_previews.py).
# `_stub_slide_deck_wording_llm` (autouse, conftest.py in this package) keeps
# `SlideDeckEngine.generate` hermetic.


async def _deck():
    result = await SlideDeckEngine().generate(SlideDeckEngineRequest(
        run_id="run-scoped-block-edit",
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
    ))
    return result.deck


def _first_block_id(deck) -> str:
    return deck.slides[0].blocks[0].block_id


async def test_edit_replaces_only_target_block_body_and_preserves_rest() -> None:
    deck = await _deck()
    block_id = _first_block_id(deck)

    updated = apply_scoped_slide_deck_block_edit(deck, block_id, "Teacher-revised block body.")

    updated_block = next(block for slide in updated.slides for block in slide.blocks if block.block_id == block_id)
    assert updated_block.body == "Teacher-revised block body."
    # Every other block is untouched, and the source deck itself is never mutated.
    other_original_bodies = [block.body for slide in deck.slides for block in slide.blocks if block.block_id != block_id]
    other_updated_bodies = [block.body for slide in updated.slides for block in slide.blocks if block.block_id != block_id]
    assert other_original_bodies == other_updated_bodies
    assert next(block for slide in deck.slides for block in slide.blocks if block.block_id == block_id).body != "Teacher-revised block body."


async def test_edit_raises_not_found_for_unknown_block_id() -> None:
    deck = await _deck()

    with pytest.raises(SlideDeckBlockNotFoundError):
        apply_scoped_slide_deck_block_edit(deck, "block-does-not-exist", "New body.")


async def test_edit_rejects_body_over_registry_max_length() -> None:
    """SDE-02's registry rule (`SlideDeckBlock.body` max_length=2000) is enforced
    server-side, independent of any client-side clamp."""
    deck = await _deck()
    block_id = _first_block_id(deck)

    with pytest.raises(SlideDeckBlockEditInvalidError):
        apply_scoped_slide_deck_block_edit(deck, block_id, "x" * 2001)


async def test_edit_rejects_empty_body_below_registry_min_length() -> None:
    deck = await _deck()
    block_id = _first_block_id(deck)

    with pytest.raises(SlideDeckBlockEditInvalidError):
        apply_scoped_slide_deck_block_edit(deck, block_id, "")


def test_slide_deck_block_edit_event_matches_shared_content_version_shape() -> None:
    event = slide_deck_block_edit_event("artifact-1", "block-1", "Clarified wording.")

    assert event["event_name"] == "teaching_pack.content_version.created"
    payload = event["payload"]
    assert isinstance(payload, dict)
    assert payload["artifact_id"] == "artifact-1"
    assert payload["block_id"] == "block-1"
    assert payload["authority"] == "teacher_edit"
    assert payload["diff"]["changed_path"] == "artifact-1.blocks[block-1]"
