"""Integration tests for compiled_json_chat tag enrichment.

Proves that compiled_json_chat enriches base tags with prompt provenance
(prompt_id, prompt_version, content_hash, compiled_hash) before delegating
to complete_json_chat.  All transport is monkeypatched — no network calls.

See test_compiled_chat.py for unit tests of the helper functions.
"""

from __future__ import annotations

from typing import Any

import pytest

import packages.agents.llm.compiled_chat as compiled_chat_mod
from packages.agents.events import clear_run
from packages.agents.llm import chat
from packages.agents.llm.compiled_chat import (
    _HASH_PREFIX_LEN,
    compiled_json_chat,
)
from packages.agents.prompts.compiler import PromptCompiler
from packages.agents.prompts.seed import create_seeded_registry


class TestCompiledJsonChatTagEnrichment:
    """Integration tests proving compiled_json_chat enriches tags correctly."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.captured_tags: list[list[str]] = []

        async def capturing_complete(
            model: str,
            messages: list[Any],
            temperature: float,
            tags: list[str],
            max_tokens: int | None = None,
        ) -> str:
            self.captured_tags.append(list(tags))
            return '{"ok": true}'

        # Patch in compiled_chat module's namespace — this is where the
        # imported reference lives after `from ... import complete_json_chat`.
        monkeypatch.setattr(compiled_chat_mod, "complete_json_chat", capturing_complete)
        clear_run("run-compiled-test")

    @pytest.mark.anyio
    async def test_tags_include_prompt_provenance_for_judge(self) -> None:
        registry = create_seeded_registry()
        compiler = PromptCompiler(registry)
        compiled = compiler.compile(module_id="judge_v1", variables={})

        await compiled_json_chat(
            model="openai/deepseek-v4-flash",
            compiled=compiled,
            messages=chat.chat_messages("system", "evaluate this"),
            temperature=0.0,
            tags=[
                "agent:reviewer",
                "run:run-compiled-test",
                "step:10",
                "task:llm_judge",
            ],
            max_tokens=256,
        )

        assert len(self.captured_tags) == 1
        tags = self.captured_tags[0]
        tag_map = {t.split(":")[0]: t.split(":", 1)[1] for t in tags if ":" in t}

        # Provenance present
        assert tag_map["prompt_id"] == "judge_v1"
        assert tag_map["prompt_version"] == "1.0.0"
        assert len(tag_map["content_hash"]) == _HASH_PREFIX_LEN
        assert len(tag_map["compiled_hash"]) == _HASH_PREFIX_LEN

        # Base tags preserved
        assert tag_map["agent"] == "reviewer"
        assert tag_map["run"] == "run-compiled-test"

    @pytest.mark.anyio
    async def test_tags_include_prompt_provenance_for_planner(self) -> None:
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="planner_v1", variables={})

        await compiled_json_chat(
            model="openai/deepseek-v4-flash",
            compiled=compiled,
            messages=chat.chat_messages("system", "plan this lesson"),
            temperature=0.3,
            tags=[
                "agent:planner",
                "run:run-compiled-test",
                "step:3",
                "task:lesson_planning",
            ],
        )

        assert len(self.captured_tags) == 1
        tags = self.captured_tags[0]
        tag_map = {t.split(":")[0]: t.split(":", 1)[1] for t in tags if ":" in t}

        assert tag_map["prompt_id"] == "planner_v1"
        assert tag_map["prompt_version"] == "1.0.0"

    @pytest.mark.anyio
    async def test_tags_include_prompt_provenance_for_content_creator(self) -> None:
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="content_creator_mcq_v1", variables={})

        await compiled_json_chat(
            model="openai/deepseek-free",
            compiled=compiled,
            messages=chat.chat_messages("system", "generate quiz"),
            temperature=0.0,
            tags=[
                "agent:content_creator",
                "run:run-compiled-test",
                "step:8",
                "task:mcq_generation",
            ],
        )

        assert len(self.captured_tags) == 1
        tags = self.captured_tags[0]
        tag_map = {t.split(":")[0]: t.split(":", 1)[1] for t in tags if ":" in t}

        assert tag_map["prompt_id"] == "content_creator_mcq_v1"
        assert tag_map["prompt_version"] == "1.0.0"

    @pytest.mark.anyio
    async def test_content_hash_prefix_in_tags_matches_full_hash(self) -> None:
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="judge_v1", variables={})

        await compiled_json_chat(
            model="openai/gpt-5.4",
            compiled=compiled,
            messages=chat.chat_messages("system", "evaluate"),
            temperature=0.0,
            tags=["agent:reviewer", "run:run-compiled-test", "step:10", "task:llm_judge"],
        )

        tags = self.captured_tags[0]
        tag_map = {t.split(":")[0]: t.split(":", 1)[1] for t in tags if ":" in t}
        full_hash = compiled.metadata.content_hash
        assert tag_map["content_hash"] == full_hash[:_HASH_PREFIX_LEN]
