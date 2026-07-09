from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def _stub_slide_deck_wording_llm(monkeypatch: pytest.MonkeyPatch):
    """Stub ContentMaterializer's real LLM wording call (SDE-01).

    Autouse (unlike content_creator's opt-in `stub_section_prose`) because every
    test in this package already exercises `SlideDeckEngine.generate`, which now
    always attempts a real `llm.complete_json_chat` call — without this, every
    test here would hit the live 9router. Echoes an empty mapping so callers fall
    back to their deterministic per-topic wording, keeping this package's tests
    fast/hermetic and their existing content assertions unchanged. Tests that need
    to exercise the actual LLM-authored path override this with their own
    `monkeypatch.setattr(llm, "complete_json_chat", ...)`.
    """
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)
