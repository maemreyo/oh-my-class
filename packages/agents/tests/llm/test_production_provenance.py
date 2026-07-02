"""Production-path provenance tests for planner and content_creator.

Proves that planner_node and content_creator_node route through
compiled_json_chat (not raw complete_json_chat) and send prompt-provenance
tags.  All transport is monkeypatched — no network calls.

These tests exercise the real node functions with a fake transport that
captures the tags passed to complete_json_chat (the inner transport called
by compiled_json_chat).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

import packages.agents.llm.compiled_chat as compiled_chat_mod
from packages.agents.events import clear_run


def _parse_tags(raw_tags: list[str]) -> dict[str, str]:
    """Parse ``key:value`` tags into a dict."""
    return {t.split(":")[0]: t.split(":", 1)[1] for t in raw_tags if ":" in t}


class _TagCapturingTransport:
    """Fake transport that captures all tags passed to complete_json_chat."""

    def __init__(self, response: str = '{"ok": true}') -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response

    async def __call__(
        self,
        model: str,
        messages: list[Any],
        temperature: float,
        tags: list[str],
        max_tokens: int | None = None,
    ) -> str:
        self.calls.append({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "tags": list(tags),
            "max_tokens": max_tokens,
        })
        return self._response


# ── Planner production path ─────────────────────────────────────────────────


class TestPlannerProvenance:
    """Proves planner_node uses compiled_json_chat and sends provenance tags."""

    VALID_PLAN = (
        '{"topic": "Photosynthesis", "grade_level": "Grade 5",'
        ' "subject": "science", "duration_minutes": 45,'
        ' "learning_objectives": ['
        '{"description": "Define photosynthesis", "bloom_level": "remember"},'
        '{"description": "Explain light reactions", "bloom_level": "understand"}],'
        ' "prerequisite_knowledge": ["basic biology"],'
        ' "learning_plan": {"phases": []},'
        ' "assessment_checkpoints": []}'
    )

    @pytest.mark.asyncio
    async def test_planner_sends_provenance_tags(self) -> None:
        """Planner node passes compiled prompt tags to the transport."""
        from typing import cast

        from packages.agents.sub_agents.planner.nodes import planner_node

        transport = _TagCapturingTransport(self.VALID_PLAN)
        clear_run("prov-planner-test")

        state = cast("dict[str, Any]", {
            "raw_request": "Teach photosynthesis to grade 5",
            "class_info": {"grade": 5, "subject": "science", "student_count": 30},
            "run_id": "prov-planner-test",
            "current_step": 3,
        })

        with patch.object(compiled_chat_mod, "complete_json_chat", transport):
            result = await planner_node(state)

        assert "lesson_plan" in result
        assert len(transport.calls) == 1
        tags = _parse_tags(transport.calls[0]["tags"])

        # Provenance tags present
        assert tags["prompt_id"] == "planner_v1"
        assert tags["prompt_version"] == "1.0.0"
        assert len(tags.get("content_hash", "")) == 16
        assert len(tags.get("compiled_hash", "")) == 16

        # Base tags preserved
        assert tags["agent"] == "planner"
        assert tags["run"] == "prov-planner-test"
        assert tags["pipeline"] == "oh-my-class"

    @pytest.mark.asyncio
    async def test_planner_no_network(self) -> None:
        """Planner node never hits the network — transport is fully fake."""
        from typing import cast

        from packages.agents.sub_agents.planner.nodes import planner_node

        transport = _TagCapturingTransport(self.VALID_PLAN)

        state = cast("dict[str, Any]", {
            "raw_request": "Teach fractions",
            "class_info": {"grade": 3, "subject": "math", "student_count": 25},
            "run_id": "no-net-test",
            "current_step": 3,
        })

        with patch.object(compiled_chat_mod, "complete_json_chat", transport):
            await planner_node(state)

        # Transport was called — no real network request happened
        assert len(transport.calls) == 1


# ── Content Creator production path ─────────────────────────────────────────


class TestContentCreatorProvenance:
    """Proves content_creator_node uses compiled_json_chat and sends provenance tags."""

    VALID_ARTIFACTS = (
        '[{"artifact_type": "lesson", "theme": "default",'
        ' "title": "Photosynthesis Lesson",'
        ' "sections": [{"type": "intro", "content": "Plants make food."}],'
        ' "metadata": {},'
        ' "accessibility": {"language": "en"}}]'
    )
    VALID_QUIZ = (
        '[{"artifact_type": "quiz", "theme": "default",'
        ' "title": "Photosynthesis Quiz",'
        ' "sections": [{"type": "question", "content": "What do plants make?"}],'
        ' "metadata": {},'
        ' "accessibility": {"language": "en"}}]'
    )

    @pytest.mark.asyncio
    async def test_content_creator_sends_provenance_tags(self) -> None:
        """Content creator passes compiled prompt tags to the transport."""
        from typing import cast

        from packages.agents.sub_agents.content_creator.nodes import content_creator_node

        transport = _TagCapturingTransport(self.VALID_ARTIFACTS)
        clear_run("prov-cc-test")

        state = cast("dict[str, Any]", {
            "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
            "research_bundle": {"sources": [], "topic": "Photosynthesis"},
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "prov-cc-test",
            "current_step": 8,
        })

        with patch.object(compiled_chat_mod, "complete_json_chat", transport):
            result = await content_creator_node(state)

        assert "artifacts" in result
        assert len(transport.calls) == 1
        tags = _parse_tags(transport.calls[0]["tags"])

        # Provenance tags present — lesson module selected for non-quiz types
        assert tags["prompt_id"] == "content_creator_lesson_v1"
        assert tags["prompt_version"] == "1.0.0"
        assert len(tags.get("content_hash", "")) == 16
        assert len(tags.get("compiled_hash", "")) == 16

        # Base tags preserved
        assert tags["agent"] == "content_creator"
        assert tags["run"] == "prov-cc-test"
        assert tags["pipeline"] == "oh-my-class"

    @pytest.mark.asyncio
    async def test_content_creator_selects_mcq_module_for_quiz(self) -> None:
        """Content creator selects mcq module when artifact_types includes quiz."""
        from typing import cast

        from packages.agents.sub_agents.content_creator.nodes import content_creator_node

        # Return a quiz-typed artifact so content_creator's per-type validation accepts
        # it; requesting quiz alone still proves the mcq module is selected.
        transport = _TagCapturingTransport(self.VALID_QUIZ)

        state = cast("dict[str, Any]", {
            "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
            "research_bundle": {"sources": []},
            "artifact_types": ["quiz"],
            "theme": "default",
            "run_id": "prov-mcq-test",
            "current_step": 8,
        })

        with patch.object(compiled_chat_mod, "complete_json_chat", transport):
            await content_creator_node(state)

        tags = _parse_tags(transport.calls[0]["tags"])
        assert tags["prompt_id"] == "content_creator_mcq_v1"

    @pytest.mark.asyncio
    async def test_content_creator_no_network(self) -> None:
        """Content creator never hits the network — transport is fully fake."""
        from typing import cast

        from packages.agents.sub_agents.content_creator.nodes import content_creator_node

        transport = _TagCapturingTransport(self.VALID_ARTIFACTS)

        state = cast("dict[str, Any]", {
            "lesson_plan": {"topic": "Fractions"},
            "research_bundle": {"sources": []},
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "no-net-cc",
            "current_step": 8,
        })

        with patch.object(compiled_chat_mod, "complete_json_chat", transport):
            await content_creator_node(state)

        assert len(transport.calls) == 1
