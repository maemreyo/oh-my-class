"""Unit tests for SDX-04's text-only best-guess alt-text generation.

Mocks `packages.agents.llm.complete_json_chat` directly (same seam
`packages/agents/tests/slide_deck_engine/test_content_materialization_llm.py`
uses for SDE-01's wording call) — no live LLM, no DB.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.gateway.media_alt_text_llm import generate_alt_text_for_image  # noqa: E402


async def test_llm_success_produces_descriptive_alt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({"alt_text": "A hand-drawn diagram of a frog's four life-cycle stages."})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await generate_alt_text_for_image(
        run_id="run-alt-text",
        filename="frog-lifecycle.png",
        tags=["biology", "diagram"],
        context="Slide about amphibian metamorphosis",
    )

    assert result == "A hand-drawn diagram of a frog's four life-cycle stages."


async def test_llm_failure_returns_none_not_a_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def raising_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        raise TimeoutError("simulated 9router timeout")

    monkeypatch.setattr(llm, "complete_json_chat", raising_complete_json_chat)

    result = await generate_alt_text_for_image(
        run_id="run-alt-text",
        filename="frog-lifecycle.png",
        tags=[],
    )

    assert result is None


async def test_llm_invalid_json_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def malformed_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return "not json at all"

    monkeypatch.setattr(llm, "complete_json_chat", malformed_complete_json_chat)

    result = await generate_alt_text_for_image(run_id="run-alt-text", filename="x.png", tags=[])

    assert result is None


async def test_empty_alt_text_response_returns_none_not_saved_as_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def empty_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({"alt_text": "   "})

    monkeypatch.setattr(llm, "complete_json_chat", empty_complete_json_chat)

    result = await generate_alt_text_for_image(run_id="run-alt-text", filename="x.png", tags=[])

    assert result is None


async def test_oversized_alt_text_is_truncated_to_schema_max(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    long_text = "A " + "very " * 200 + "long description."  # > 500 chars

    async def oversized_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({"alt_text": long_text})

    monkeypatch.setattr(llm, "complete_json_chat", oversized_complete_json_chat)

    result = await generate_alt_text_for_image(run_id="run-alt-text", filename="x.png", tags=[])

    assert result is not None
    assert len(result) <= 500
