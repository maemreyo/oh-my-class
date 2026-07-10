from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from packages.agents.slide_deck_engine.phases.block_rewrite_llm import (
    BLOCK_REWRITE_PRESETS,
    BlockRewriteInstructionError,
    generate_slide_deck_block_rewrite,
    resolve_rewrite_instruction,
)

if TYPE_CHECKING:
    pass

# SDE-08: preset->instruction resolution and the real LLM call, mirroring
# `test_content_materialization_llm.py`'s conventions for SDE-01's sibling call.


def test_preset_resolves_to_its_fixed_instruction_template() -> None:
    for preset, instruction in BLOCK_REWRITE_PRESETS.items():
        assert resolve_rewrite_instruction(preset=preset, freeform=None) == instruction


def test_unknown_preset_raises() -> None:
    with pytest.raises(BlockRewriteInstructionError):
        resolve_rewrite_instruction(preset="not_a_real_preset", freeform=None)


def test_freeform_text_is_used_verbatim_when_no_preset_given() -> None:
    assert resolve_rewrite_instruction(preset=None, freeform="  Make it rhyme.  ") == "Make it rhyme."


def test_blank_freeform_and_no_preset_raises() -> None:
    with pytest.raises(BlockRewriteInstructionError):
        resolve_rewrite_instruction(preset=None, freeform="   ")


async def test_llm_authored_rewrite_reaches_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({"body": "LLM_REWRITE_MARKER"})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await generate_slide_deck_block_rewrite(
        run_id="run-block-rewrite",
        current_body="Fractions are parts of a whole.",
        instruction=BLOCK_REWRITE_PRESETS["shorter"],
    )

    assert result == "LLM_REWRITE_MARKER"


async def test_llm_timeout_returns_none_not_a_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def raising_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        raise TimeoutError("simulated 9router timeout")

    monkeypatch.setattr(llm, "complete_json_chat", raising_complete_json_chat)

    result = await generate_slide_deck_block_rewrite(
        run_id="run-block-rewrite",
        current_body="Fractions are parts of a whole.",
        instruction=BLOCK_REWRITE_PRESETS["shorter"],
    )

    assert result is None


async def test_llm_invalid_json_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def malformed_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return "not json at all"

    monkeypatch.setattr(llm, "complete_json_chat", malformed_complete_json_chat)

    result = await generate_slide_deck_block_rewrite(
        run_id="run-block-rewrite",
        current_body="Fractions are parts of a whole.",
        instruction=BLOCK_REWRITE_PRESETS["shorter"],
    )

    assert result is None


async def test_empty_body_response_is_treated_as_no_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({"body": ""})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await generate_slide_deck_block_rewrite(
        run_id="run-block-rewrite",
        current_body="Fractions are parts of a whole.",
        instruction=BLOCK_REWRITE_PRESETS["shorter"],
    )

    assert result is None
