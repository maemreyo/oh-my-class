"""SDE-08: single-block AI-assisted rewrite LLM call.

Mirrors `content_materialization_llm.py::generate_slide_deck_wording`'s exact
calling convention (same `AgentRuntime`/`complete_json_with_retries` +
`extract_json_text` parse pattern) -- one more schema-bound wording call, not
a new calling convention.

Preset instructions (`BLOCK_REWRITE_PRESETS`) and freeform teacher text both
resolve through the same `resolve_rewrite_instruction` function into a single
instruction string, which is the only input `generate_slide_deck_block_rewrite`
accepts -- there is deliberately no separate/looser freeform code path (SDE-08
AC1).
"""

from __future__ import annotations

import json
from typing import Final

from pydantic import BaseModel, ConfigDict

# Fixed preset -> instruction-template map (SDE-08 AC1). Keys are the stable
# identifiers the frontend preset picker sends; values are the actual
# instruction text handed to the LLM. Add a preset by adding one entry here --
# never a second function/path.
BLOCK_REWRITE_PRESETS: Final[dict[str, str]] = {
    "shorter": (
        "Rewrite the block to be noticeably shorter and more concise, while "
        "preserving its full meaning."
    ),
    "add_example": (
        "Rewrite the block to include one brief, concrete, age-appropriate "
        "example illustrating the idea."
    ),
    "simplify": (
        "Rewrite the block using simpler vocabulary and shorter sentences, "
        "suitable for a younger reader."
    ),
}


class BlockRewriteInstructionError(ValueError):
    """Raised when neither a known preset key nor freeform text is given."""


def resolve_rewrite_instruction(*, preset: str | None, freeform: str | None) -> str:
    """Resolve a preset key or freeform text into one instruction string.

    Preset takes precedence when both are somehow given (the frontend UI only
    ever sends one at a time). Freeform text is trimmed but otherwise passed
    through unchanged -- it flows into the exact same
    `generate_slide_deck_block_rewrite` call presets do, no separate
    validation path (SDE-08 AC1).
    """
    if preset is not None:
        instruction = BLOCK_REWRITE_PRESETS.get(preset)
        if instruction is None:
            msg = f"unknown rewrite preset: {preset!r}"
            raise BlockRewriteInstructionError(msg)
        return instruction
    freeform_text = (freeform or "").strip()
    if not freeform_text:
        msg = "either a preset key or non-empty freeform instruction is required"
        raise BlockRewriteInstructionError(msg)
    return freeform_text


_SYSTEM_PROMPT: Final = (
    "You are an expert K-12 teaching content writer revising ONE piece of "
    "classroom slide-deck text at a teacher's request. Rewrite ONLY the text "
    "given to you, grounded in its existing meaning -- do not invent new facts, "
    "names, or numbers, and do not change its topic. Keep it classroom-ready and "
    "age-appropriate.\n\n"
    'Respond ONLY with a JSON object of the exact shape {"body": "<rewritten '
    'text>"}. No prose, no explanation, no markdown fences.'
)


class SlideDeckBlockRewriteResponse(BaseModel):
    """Schema-bound LLM response contract for a single block rewrite.

    `body` defaults to "" ("not provided"); the caller treats an empty
    response as a failed rewrite (same graceful-degradation shape as
    `SlideDeckWordingResponse`), never a silently-blanked block.
    """

    model_config = ConfigDict(extra="ignore")

    body: str = ""


async def generate_slide_deck_block_rewrite(
    *,
    run_id: str,
    current_body: str,
    instruction: str,
) -> str | None:
    """Call llm_client to rewrite one block's body; None on timeout/invalid/empty.

    Scoped to exactly one block's text in, one block's text out -- there is no
    deck/slide context in the prompt for the model to act on, so it has
    nothing to rewrite beyond the given `current_body` (SDE-08 AC2).
    """
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    user_prompt = f"Current text:\n{current_body}\n\nInstruction: {instruction}"
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="slide_deck_engine",
        run_id=run_id,
        step=stage_number(StageEnum.ARTIFACT_WORKFLOW),
        step_label=StageEnum.ARTIFACT_WORKFLOW.value,
        model=MODELS.content_creator,
        base_temperature=0.4,
        retry_temperature=0.2,
    ))
    messages = runtime.messages(_SYSTEM_PROMPT, user_prompt)

    def parse(content: str) -> str:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object with a body field")
        return SlideDeckBlockRewriteResponse.model_validate(data).body

    try:
        body = await runtime.complete_json_with_retries(
            messages=messages,
            parse=parse,
            retry_messages=lambda _err, _content: runtime.messages(
                _SYSTEM_PROMPT,
                'Invalid response. Return ONLY the JSON object {"body": "<rewritten text>"}.',
            ),
            extra_tags=("phase:content_materialization", "slide_deck_block_rewrite"),
        )
    except Exception:  # noqa: BLE001 - any LLM failure surfaces as "no candidate", never a placeholder
        return None
    return body or None


if __name__ == "__main__":
    # ponytail: smallest runnable check for the pure resolver, no LLM call.
    _shorter = BLOCK_REWRITE_PRESETS["shorter"]
    assert resolve_rewrite_instruction(preset="shorter", freeform=None) == _shorter
    assert resolve_rewrite_instruction(preset=None, freeform="  make it rhyme  ") == "make it rhyme"
    try:
        resolve_rewrite_instruction(preset=None, freeform="   ")
    except BlockRewriteInstructionError:
        pass
    else:
        raise AssertionError("expected BlockRewriteInstructionError for blank freeform")
    try:
        resolve_rewrite_instruction(preset="not_a_real_preset", freeform=None)
    except BlockRewriteInstructionError:
        pass
    else:
        raise AssertionError("expected BlockRewriteInstructionError for unknown preset")
    print("block_rewrite_llm self-check OK")
