from __future__ import annotations

import json

import pytest


@pytest.fixture
def stub_section_prose(monkeypatch: pytest.MonkeyPatch):
    """Stub content_creator's per-artifact prose LLM call (LIC-02).

    Echoes an empty mapping so callers fall back to their deterministic
    placeholder text — tests that don't assert on exact prose stay fast and
    hermetic without needing a live LLM.

    Also covers `ContentMaterializer`'s slide-deck wording call (SDE-01): both
    go through the same underlying `llm.complete_json_chat`, so slide_deck tests
    that route through the real hierarchical/graph entrypoints request this
    fixture too instead of duplicating the stub.
    """
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return json.dumps({})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)
