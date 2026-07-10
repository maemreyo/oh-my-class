"""Ephemeral AI rewrite proposals over V2 block_document payloads (ADR-055).

Nothing here is persisted. The proposal is returned directly to the caller
and only reaches storage if the teacher accepts it by calling the normal
edit endpoint with authority="ai_assisted_edit" -- there is deliberately no
separate write path for AI-authored content, which is the whole mechanism
behind "AI changes remain ephemeral until accepted."

Reuses `generate_slide_deck_block_rewrite` (SDE-08) as-is: despite the name,
it is a plain text-in/text-out rewrite call with no slide-deck-specific
context, so one block-document lookup here is the only new code needed to
generalize scoped AI rewrite past slide decks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from packages.agents.slide_deck_engine.phases.block_rewrite_llm import (
    BlockRewriteInstructionError,
    generate_slide_deck_block_rewrite,
    resolve_rewrite_instruction,
)

if TYPE_CHECKING:
    from common.contracts.artifact_document import ArtifactDocument, DocumentBlock

__all__ = [
    "BlockNotFoundError",
    "BlockRewriteInstructionError",
    "RewriteProposal",
    "UnsupportedPayloadForRewriteError",
    "propose_block_rewrite",
]


class BlockNotFoundError(LookupError):
    def __init__(self, entity_id: str) -> None:
        self.entity_id = entity_id
        super().__init__(entity_id)


class UnsupportedPayloadForRewriteError(ValueError):
    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(f"{artifact_type} does not use a block_document payload")


class RewriteUnavailableError(RuntimeError):
    """Raised when the LLM call times out or returns an invalid/empty result."""


@dataclass(frozen=True, slots=True)
class RewriteProposal:
    entity_id: str
    before: str
    after: str


async def propose_block_rewrite(
    *,
    run_id: str,
    document: ArtifactDocument,
    content_entity_id: str,
    preset: str | None = None,
    instruction: str | None = None,
) -> RewriteProposal:
    """Generate a proposed rewrite of one block, without touching persistence."""
    if document.payload.payload_kind != "block_document":
        raise UnsupportedPayloadForRewriteError(document.artifact_type)
    block = _find_block(document, content_entity_id)
    resolved_instruction = resolve_rewrite_instruction(preset=preset, freeform=instruction)
    rewritten = await generate_slide_deck_block_rewrite(
        run_id=run_id, current_body=block.text, instruction=resolved_instruction,
    )
    if rewritten is None:
        raise RewriteUnavailableError(content_entity_id)
    return RewriteProposal(entity_id=content_entity_id, before=block.text, after=rewritten)


def _find_block(document: ArtifactDocument, entity_id: str) -> DocumentBlock:
    for section in document.payload.sections or []:
        for block in section.blocks:
            if block.entity_id == entity_id:
                return block
    raise BlockNotFoundError(entity_id)
