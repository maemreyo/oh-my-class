"""Tests for content_creator agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.nodes import (
    content_creator_node as generate_artifacts,
)
from packages.agents.sub_agents.content_creator.nodes import (
    validate_no_cdn,
    validate_no_pii,
)
from packages.agents.teaching_pack.stages import StageEnum

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_llm_mock(
    return_value: str | None = None,
    side_effect: Exception | None = None,
) -> AsyncMock:
    if side_effect is not None:
        return AsyncMock(side_effect=side_effect)
    return AsyncMock(return_value=return_value)


def _make_state(**overrides) -> dict[str, Any]:
    base = {
        "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
        "research_bundle": {"sources": [], "topic": "Photosynthesis"},
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "test-run-001",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
    }
    base.update(overrides)
    return base


VALID_ARTIFACT = {
    "artifact_type": "lesson",
    "theme": "default",
    "title": "Photosynthesis Lesson",
    "sections": [{"type": "intro", "content": "Plants convert sunlight to glucose."}],
    "metadata": {},
    "accessibility": {"language": "en"},
}

VALID_ARTIFACT_JSON = json.dumps(VALID_ARTIFACT)
VALID_ARTIFACT_WRAPPED = f"```json\n{json.dumps([VALID_ARTIFACT])}\n```"
VALID_ARTIFACT_ARRAY_JSON = json.dumps([VALID_ARTIFACT])


# ── ContentCreatorAgent ───────────────────────────────────────────────────────

class TestContentCreatorAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_artifact_content(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1
        artifact = ArtifactContent.model_validate(result["artifacts"][0])
        assert artifact.artifact_type == "lesson"

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert result["artifacts"][0]["title"] == "Photosynthesis Lesson"

    @pytest.mark.asyncio
    async def test_parses_generic_code_fence(self):
        wrapped = f"```\n{VALID_ARTIFACT_ARRAY_JSON}\n```"
        mock_llm = _make_llm_mock(return_value=wrapped)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_parses_bare_json_array(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_ARRAY_JSON)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result

    @pytest.mark.asyncio
    async def test_wraps_single_artifact_dict_in_list(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_JSON)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert len(result["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        mock_llm = _make_llm_mock(return_value="not valid json")
        with (
            patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Content creator failed"),
        ):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

    @pytest.mark.asyncio
    async def test_llm_error_raises_value_error(self):
        mock_llm = _make_llm_mock(side_effect=RuntimeError("API timeout"))
        with (
            patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Content creator failed"),
        ):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

    @pytest.mark.asyncio
    async def test_calls_llm_with_correct_model(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert mock_llm.call_args.kwargs["model"] == "4omc"

    @pytest.mark.asyncio
    async def test_metadata_tags_include_run_id(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state(run_id="run-xyz")))

        tags = mock_llm.call_args.kwargs["tags"]
        assert any("run-xyz" in t for t in tags)
        assert any("agent:content_creator" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)

    @pytest.mark.asyncio
    async def test_missing_lesson_plan_uses_empty_dict(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state(lesson_plan=None)))  # noqa: E501

        mock_llm.assert_awaited_once()
        assert "artifacts" in result

    @pytest.mark.asyncio
    async def test_missing_artifact_types_defaults_to_lesson(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state(artifact_types=None)))

        user_msg = mock_llm.call_args.kwargs["messages"][1]["content"]
        assert "lesson" in user_msg

    @pytest.mark.asyncio
    async def test_theme_forwarded_to_prompt(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state(theme="ocean")))

        user_msg = mock_llm.call_args.kwargs["messages"][1]["content"]
        assert "ocean" in user_msg

    @pytest.mark.asyncio
    async def test_artifact_validates_against_schema(self):
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        for artifact_dict in result["artifacts"]:
            artifact = ArtifactContent.model_validate(artifact_dict)
            assert artifact.artifact_type in ("lesson", "worksheet", "quiz", "drill", "recap", "infographic")  # noqa: E501
            assert len(artifact.title) >= 3

    @pytest.mark.asyncio
    async def test_system_prompt_from_external_file(self):
        """Regression: system prompt must come from prompts/system.md, not hardcoded."""
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

        system_msg = mock_llm.call_args.kwargs["messages"][0]["content"]
        # system.md contains "Rich Component Model" section — hardcoded prompt did not
        assert "Rich Component Model" in system_msg or "RCM" in system_msg
        # system.md contains the complete valid example
        assert "Phân số tương đương" in system_msg
        # JSON-only suffix appended
        assert "CRITICAL" in system_msg

    @pytest.mark.asyncio
    async def test_temperature_is_03(self):
        """Temperature must be 0.3 for structured JSON output (not 0.7)."""
        mock_llm = _make_llm_mock(return_value=VALID_ARTIFACT_WRAPPED)
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert mock_llm.call_args.kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_retry_includes_failed_output(self):
        """Retry prompt must include the failed LLM output for self-repair."""
        from packages.agents.sub_agents.content_creator.nodes import _retry_single_artifact_prompt

        failed_output = '{"bad": "json"}'
        result = _retry_single_artifact_prompt("base prompt", "lesson", ValueError("missing field"), failed_output)
        assert "Previous output" in result or "previous output" in result
        assert failed_output in result

    @pytest.mark.asyncio
    async def test_retry_without_failed_output(self):
        """Retry prompt works when no previous output available."""
        from packages.agents.sub_agents.content_creator.nodes import _retry_single_artifact_prompt

        result = _retry_single_artifact_prompt("base prompt", "lesson", ValueError("error"), None)
        assert "base prompt" in result
        assert "Validation error" in result or "validation error" in result

    @pytest.mark.asyncio
    async def test_recovers_after_interrupted_generation_stream(self):
        interrupted_then_valid = AsyncMock(side_effect=[
            RuntimeError("stream interrupted mid-generation"),
            VALID_ARTIFACT_JSON,
        ])
        with patch("packages.agents.llm.compiled_chat.complete_json_chat", interrupted_then_valid):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert result["artifacts"][0]["title"] == "Photosynthesis Lesson"
        assert interrupted_then_valid.await_count == 2
        first_tags = interrupted_then_valid.await_args_list[0].kwargs["tags"]
        second_tags = interrupted_then_valid.await_args_list[1].kwargs["tags"]
        assert "attempt:1" in first_tags
        assert "attempt:2" in second_tags


# ── validate_no_cdn ───────────────────────────────────────────────────────────

class TestValidateNoCdn:
    def test_detects_cdn_dot(self):
        artifacts = [{"content": "loaded from cdn.example.com"}]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 1
        assert "CDN" in issues[0]

    def test_detects_cloudflare(self):
        artifacts = [{"content": "via cloudflare.com"}]
        issues = validate_no_cdn(artifacts)
        assert any("cloudflare.com" in i for i in issues)

    def test_detects_jsdelivr(self):
        artifacts = [{"content": "jsdelivr.net/npm/bootstrap"}]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 1

    def test_detects_unpkg(self):
        artifacts = [{"content": "unpkg.com/react"}]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 1

    def test_clean_artifact_returns_empty(self):
        artifacts = [{"content": "No external references here."}]
        issues = validate_no_cdn(artifacts)
        assert issues == []

    def test_multiple_artifacts_reported_with_index(self):
        artifacts = [
            {"content": "clean"},
            {"content": "cdn.example.com"},
        ]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 1
        assert "artifact 1" in issues[0]


# ── validate_no_pii ───────────────────────────────────────────────────────────

class TestValidateNoPii:
    def test_detects_email(self):
        artifacts = [{"content": "Contact john@example.com for help"}]
        issues = validate_no_pii(artifacts)
        assert len(issues) == 1
        assert "Email" in issues[0]

    def test_detects_phone_dashes(self):
        artifacts = [{"content": "Call 555-123-4567"}]
        issues = validate_no_pii(artifacts)
        assert len(issues) == 1
        assert "Phone" in issues[0]

    def test_detects_phone_dots(self):
        artifacts = [{"content": "555.123.4567"}]
        issues = validate_no_pii(artifacts)
        assert any("Phone" in i for i in issues)

    def test_clean_artifact_returns_empty(self):
        artifacts = [{"content": "No personal information here."}]
        issues = validate_no_pii(artifacts)
        assert issues == []

    def test_multiple_violations_reported(self):
        artifacts = [{"content": "email: a@b.com phone: 555-123-4567"}]
        issues = validate_no_pii(artifacts)
        assert len(issues) == 2


# ── Tools ─────────────────────────────────────────────────────────────────────

class TestContentCreatorTools:
    @pytest.mark.asyncio
    async def test_read_file_returns_content(self):
        from packages.agents.sub_agents.content_creator.tools import read_file
        from packages.agents.sub_agents.content_creator.tools import write_file

        path = ".scratch/test-content-creator-read.txt"
        await write_file(path, "hello world", overwrite=True)
        content = await read_file(path)
        assert content == "hello world"

    @pytest.mark.asyncio
    async def test_write_file_creates_file(self):
        from packages.agents.sub_agents.content_creator.tools import write_file

        path = Path(".scratch/test-content-creator-out.txt")
        path.unlink(missing_ok=True)
        result = await write_file(str(path), "artifact content")
        assert result is True
        assert path.read_text() == "artifact content"

    @pytest.mark.asyncio
    async def test_write_file_no_overwrite_by_default(self):
        from packages.agents.sub_agents.content_creator.tools import write_file

        path = Path(".scratch/test-content-creator-existing.txt")
        path.write_text("original")
        result = await write_file(str(path), "new content")
        assert result is False
        assert path.read_text() == "original"

    @pytest.mark.asyncio
    async def test_write_file_overwrite_flag(self):
        from packages.agents.sub_agents.content_creator.tools import write_file

        path = Path(".scratch/test-content-creator-overwrite.txt")
        path.write_text("original")
        result = await write_file(str(path), "new content", overwrite=True)
        assert result is True
        assert path.read_text() == "new content"


# ── Prompts ───────────────────────────────────────────────────────────────────

class TestContentCreatorPrompts:
    def test_prompt_contains_artifact_types(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        content_creator_system_prompt = load_system_prompt()

        for artifact_type in ("lesson", "worksheet", "quiz", "drill", "recap", "infographic"):
            assert artifact_type in content_creator_system_prompt

    def test_prompt_mentions_no_html(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        content_creator_system_prompt = load_system_prompt()

        assert "HTML" in content_creator_system_prompt

    def test_prompt_mentions_teacher_only(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        content_creator_system_prompt = load_system_prompt()

        assert "teacher_only" in content_creator_system_prompt

    def test_prompt_mentions_no_cdn(self):
        from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
        content_creator_system_prompt = load_system_prompt()

        assert "CDN" in content_creator_system_prompt
