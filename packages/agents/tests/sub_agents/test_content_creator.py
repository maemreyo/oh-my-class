"""Tests for content_creator agent."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.nodes import (
    content_creator_node as generate_artifacts,
)
from packages.agents.sub_agents.content_creator.nodes import (
    validate_no_cdn,
    validate_no_pii,
)

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


def _make_litellm_mock(return_value=None, side_effect=None) -> MagicMock:
    mock_module = MagicMock()
    if side_effect is not None:
        mock_module.acompletion = AsyncMock(side_effect=side_effect)
    else:
        mock_module.acompletion = AsyncMock(return_value=return_value)
    return mock_module


def _make_state(**overrides) -> dict[str, Any]:
    base = {
        "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
        "research_bundle": {"sources": [], "topic": "Photosynthesis"},
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "test-run-001",
        "current_step": 8,
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
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1
        artifact = ArtifactContent.model_validate(result["artifacts"][0])
        assert artifact.artifact_type == "lesson"

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert result["artifacts"][0]["title"] == "Photosynthesis Lesson"

    @pytest.mark.asyncio
    async def test_parses_generic_code_fence(self):
        wrapped = f"```\n{VALID_ARTIFACT_ARRAY_JSON}\n```"
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(wrapped))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_parses_bare_json_array(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_ARRAY_JSON))  # noqa: E501
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert "artifacts" in result

    @pytest.mark.asyncio
    async def test_wraps_single_artifact_dict_in_list(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_JSON))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert len(result["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response("not valid json"))
        with patch.dict(sys.modules, {"litellm": mock_litellm}), pytest.raises(ValueError, match="Content creator agent failed"):  # noqa: E501
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

    @pytest.mark.asyncio
    async def test_raises_value_error_on_llm_error(self):
        mock_litellm = _make_litellm_mock(side_effect=RuntimeError("API timeout"))
        with patch.dict(sys.modules, {"litellm": mock_litellm}), pytest.raises(ValueError, match="Content creator agent failed"):  # noqa: E501
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

    @pytest.mark.asyncio
    async def test_calls_litellm_with_correct_model(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await generate_artifacts(cast("ContentCreatorState", _make_state()))

        assert mock_litellm.acompletion.call_args.kwargs["model"] == "openai/f.light"

    @pytest.mark.asyncio
    async def test_metadata_tags_include_run_id(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await generate_artifacts(cast("ContentCreatorState", _make_state(run_id="run-xyz")))

        tags = mock_litellm.acompletion.call_args.kwargs["extra_body"]["metadata"]["tags"]
        assert any("run-xyz" in t for t in tags)
        assert any("agent:content_creator" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)

    @pytest.mark.asyncio
    async def test_missing_lesson_plan_uses_empty_dict(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state(lesson_plan=None)))  # noqa: E501

        mock_litellm.acompletion.assert_awaited_once()
        assert "artifacts" in result

    @pytest.mark.asyncio
    async def test_missing_artifact_types_defaults_to_lesson(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await generate_artifacts(cast("ContentCreatorState", _make_state(artifact_types=None)))

        user_msg = mock_litellm.acompletion.call_args.kwargs["messages"][1]["content"]
        assert "lesson" in user_msg

    @pytest.mark.asyncio
    async def test_theme_forwarded_to_prompt(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await generate_artifacts(cast("ContentCreatorState", _make_state(theme="ocean")))

        user_msg = mock_litellm.acompletion.call_args.kwargs["messages"][1]["content"]
        assert "ocean" in user_msg

    @pytest.mark.asyncio
    async def test_artifact_validates_against_schema(self):
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_ARTIFACT_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await generate_artifacts(cast("ContentCreatorState", _make_state()))

        for artifact_dict in result["artifacts"]:
            artifact = ArtifactContent.model_validate(artifact_dict)
            assert artifact.artifact_type in ("lesson", "worksheet", "quiz", "drill", "recap", "infographic")  # noqa: E501
            assert len(artifact.title) >= 3


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
    async def test_read_file_returns_content(self, tmp_path):
        from packages.agents.sub_agents.content_creator.tools import read_file

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        content = await read_file(str(f))
        assert content == "hello world"

    @pytest.mark.asyncio
    async def test_write_file_creates_file(self, tmp_path):
        from packages.agents.sub_agents.content_creator.tools import write_file

        path = str(tmp_path / "out.txt")
        result = await write_file(path, "artifact content")
        assert result is True
        with open(path) as f:
            assert f.read() == "artifact content"

    @pytest.mark.asyncio
    async def test_write_file_no_overwrite_by_default(self, tmp_path):
        from packages.agents.sub_agents.content_creator.tools import write_file

        f = tmp_path / "existing.txt"
        f.write_text("original")
        result = await write_file(str(f), "new content")
        assert result is False
        assert f.read_text() == "original"

    @pytest.mark.asyncio
    async def test_write_file_overwrite_flag(self, tmp_path):
        from packages.agents.sub_agents.content_creator.tools import write_file

        f = tmp_path / "existing.txt"
        f.write_text("original")
        result = await write_file(str(f), "new content", overwrite=True)
        assert result is True
        assert f.read_text() == "new content"


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
