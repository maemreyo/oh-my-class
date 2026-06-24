"""Tests for researcher agent."""

import json
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from common.contracts.research_bundle import ResearchBundle


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


def _make_state(**overrides) -> dict:
    base = {
        "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
        "research_policy": "standard",
        "run_id": "test-run-001",
        "current_step": 7,
    }
    base.update(overrides)
    return base


VALID_BUNDLE_JSON = json.dumps({
    "topic": "Photosynthesis",
    "sources": [
        {"title": "Source 1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
        {"title": "Source 2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
    ],
    "key_findings": ["Plants convert sunlight to glucose"],
    "research_policy": "standard",
})

VALID_BUNDLE_WRAPPED = f"```json\n{VALID_BUNDLE_JSON}\n```"
VALID_BUNDLE_GENERIC_FENCE = f"```\n{VALID_BUNDLE_JSON}\n```"


# ── ResearcherAgent ───────────────────────────────────────────────────────────

class TestResearcherAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_research_bundle(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state())

        assert "research_bundle" in result
        bundle = ResearchBundle.model_validate(result["research_bundle"])
        assert bundle.topic == "Photosynthesis"
        assert len(bundle.sources) == 2

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state())

        assert result["research_bundle"]["topic"] == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_parses_generic_code_fence(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_GENERIC_FENCE))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state())

        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_parses_bare_json(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_JSON))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state())

        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response("not json"))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            with pytest.raises(ValueError, match="Invalid JSON"):
                await research_sources(_make_state())

    @pytest.mark.asyncio
    async def test_raises_value_error_on_llm_error(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(side_effect=RuntimeError("API timeout"))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            with pytest.raises(ValueError, match="Researcher agent failed"):
                await research_sources(_make_state())

    @pytest.mark.asyncio
    async def test_raises_on_too_few_sources(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        bad_bundle = json.dumps({
            "topic": "T",
            "sources": [{"title": "Only one", "credibility_score": 0.9, "verification_status": "VERIFIED"}],
        })
        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(bad_bundle))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            with pytest.raises(ValueError, match="Researcher agent failed"):
                await research_sources(_make_state())

    @pytest.mark.asyncio
    async def test_missing_lesson_plan_uses_default_topic(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state(lesson_plan=None))

        mock_litellm.acompletion.assert_awaited_once()
        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_calls_litellm_with_correct_model(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await research_sources(_make_state())

        assert mock_litellm.acompletion.call_args.kwargs["model"] == "f.light"

    @pytest.mark.asyncio
    async def test_metadata_tags_include_run_id(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await research_sources(_make_state(run_id="run-abc"))

        tags = mock_litellm.acompletion.call_args.kwargs["extra_body"]["metadata"]["tags"]
        assert any("run-abc" in t for t in tags)
        assert any("agent:researcher" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)

    @pytest.mark.asyncio
    async def test_research_policy_forwarded_to_prompt(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            await research_sources(_make_state(research_policy="rigorous"))

        user_msg = mock_litellm.acompletion.call_args.kwargs["messages"][1]["content"]
        assert "rigorous" in user_msg

    @pytest.mark.asyncio
    async def test_bundle_sources_have_verification_status(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_litellm = _make_litellm_mock(return_value=_make_mock_response(VALID_BUNDLE_WRAPPED))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            result = await research_sources(_make_state())

        bundle = ResearchBundle.model_validate(result["research_bundle"])
        for source in bundle.sources:
            assert source.verification_status in ("VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN")


# ── Tools ─────────────────────────────────────────────────────────────────────

class TestResearcherTools:
    @pytest.mark.asyncio
    async def test_web_search_returns_results(self):
        from packages.agents.sub_agents.researcher.tools import web_search

        results = await web_search("photosynthesis", num_results=3)
        assert len(results) == 3
        assert all("title" in r for r in results)
        assert all("url" in r for r in results)
        assert all("snippet" in r for r in results)

    @pytest.mark.asyncio
    async def test_web_search_respects_num_results(self):
        from packages.agents.sub_agents.researcher.tools import web_search

        results = await web_search("test", num_results=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_web_fetch_returns_string(self):
        from packages.agents.sub_agents.researcher.tools import web_fetch

        content = await web_fetch("https://example.com")
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_web_fetch_includes_url(self):
        from packages.agents.sub_agents.researcher.tools import web_fetch

        content = await web_fetch("https://example.com/test")
        assert "example.com" in content


# ── Prompts ───────────────────────────────────────────────────────────────────

class TestResearcherPrompts:
    def test_prompt_contains_fact_protocol(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt; RESEARCHER_SYSTEM_PROMPT = load_system_prompt()

        assert "FACT" in RESEARCHER_SYSTEM_PROMPT
        assert "Find" in RESEARCHER_SYSTEM_PROMPT
        assert "Assess" in RESEARCHER_SYSTEM_PROMPT
        assert "Cross-reference" in RESEARCHER_SYSTEM_PROMPT
        assert "Tag" in RESEARCHER_SYSTEM_PROMPT

    def test_prompt_contains_verification_statuses(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt; RESEARCHER_SYSTEM_PROMPT = load_system_prompt()

        for status in ("VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"):
            assert status in RESEARCHER_SYSTEM_PROMPT

    def test_prompt_contains_research_policies(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt; RESEARCHER_SYSTEM_PROMPT = load_system_prompt()

        assert "basic" in RESEARCHER_SYSTEM_PROMPT
        assert "standard" in RESEARCHER_SYSTEM_PROMPT
        assert "rigorous" in RESEARCHER_SYSTEM_PROMPT

    def test_prompt_contains_output_schema(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt; RESEARCHER_SYSTEM_PROMPT = load_system_prompt()

        assert "credibility_score" in RESEARCHER_SYSTEM_PROMPT
        assert "verification_status" in RESEARCHER_SYSTEM_PROMPT
