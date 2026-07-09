"""SDE-04: the single business function for a scoped slide-deck block edit.

Shared verbatim by both entry points -- the gate-resume flow
(``packages/agents/teaching_pack/scoped_regeneration.py``) and the standalone
snapshot-edit endpoint (``services/gateway/routers/teaching_pack_previews.py``)
-- so the edit semantics and SDE-02 registry-bound validation live in exactly
one place regardless of which caller reaches it. Mirrors
``apply_scoped_section_edit``'s role for flat-section artifacts, but slide
decks are ``slides[].blocks[]``, not a flat ``sections`` list, so that
function cannot be reused as-is (ADR-047 decisions 5/6/9).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from common.contracts.slide_deck import SlideDeckData

    type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
    type JsonObject = dict[str, JsonValue]


class SlideDeckBlockNotFoundError(ValueError):
    """Raised when no block in the deck matches the requested `block_id`."""

    def __init__(self, block_id: str) -> None:
        self.block_id = block_id
        super().__init__(f"slide deck block not found: {block_id!r}")


class SlideDeckBlockEditInvalidError(ValueError):
    """Raised when `new_content` violates the block's own registry constraints."""

    def __init__(self, block_id: str, reason: str) -> None:
        self.block_id = block_id
        super().__init__(f"invalid edit for slide deck block {block_id!r}: {reason}")


def apply_scoped_slide_deck_block_edit(
    deck: SlideDeckData,
    block_id: str,
    new_content: str,
) -> SlideDeckData:
    """Return a new deck with `block_id`'s body replaced by `new_content`.

    Re-validates the edited block through its own pydantic `Field` bounds
    (SDE-02's registry rule for `SlideDeckBlock.body`, `min_length=1,
    max_length=2000`) via an explicit `model_validate` call -- `model_copy`
    alone skips validation entirely, so this is the actual server-side
    enforcement point. Client-side validation (SDE-03's `clampOrReject`) is
    never sufficient alone. Never mutates `deck`.

    Raises:
        SlideDeckBlockNotFoundError: no block in the deck matches `block_id`.
        SlideDeckBlockEditInvalidError: `new_content` fails the block's bounds.
    """
    found = False
    next_slides = []
    for slide in deck.slides:
        if not any(block.block_id == block_id for block in slide.blocks):
            next_slides.append(slide)
            continue
        found = True
        next_blocks = []
        for block in slide.blocks:
            if block.block_id != block_id:
                next_blocks.append(block)
                continue
            try:
                next_blocks.append(
                    type(block).model_validate({**block.model_dump(mode="json"), "body": new_content}),
                )
            except ValidationError as exc:
                raise SlideDeckBlockEditInvalidError(block_id, str(exc)) from exc
        next_slides.append(slide.model_copy(update={"blocks": next_blocks}))
    if not found:
        raise SlideDeckBlockNotFoundError(block_id)
    return deck.model_copy(update={"slides": next_slides})


def slide_deck_block_edit_event(
    artifact_id: str,
    block_id: str,
    rationale: str,
    *,
    authority: str = "teacher_edit",
) -> JsonObject:
    """Build the shared `content_version.created` event payload.

    Mirrors `apply_scoped_section_edit`'s event shape exactly (same
    `event_name`, same `authority`/`diff` payload keys) so both entry points
    emit an identical event regardless of which one is called. `authority`
    defaults to `"teacher_edit"`; SDE-08's AI-assisted rewrite passes
    `"ai_assisted_edit"` through the same helper.
    """
    return {
        "event_name": "teaching_pack.content_version.created",
        "payload": {
            "artifact_id": artifact_id,
            "block_id": block_id,
            "authority": authority,
            "diff": {
                "status": "teacher_block_edit",
                "changed_path": f"{artifact_id}.blocks[{block_id}]",
                "rationale": rationale,
            },
        },
    }
