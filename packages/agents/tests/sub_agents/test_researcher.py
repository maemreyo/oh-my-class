"""Tests for researcher agent."""

import contextlib
import json
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.research_bundle import ResearchBundle
from packages.agents.teaching_pack.stages import StageEnum

if TYPE_CHECKING:
    from packages.agents.sub_agents.researcher.state import ResearcherState

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
        "research_policy": "standard",
        "run_id": "test-run-001",
        "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
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
SEARCH_RESULTS = [
    {
        "title": "Source 1",
        "url": "https://example.edu/one",
        "snippet": "Alpha",
        "verification_status": "UNCERTAIN",
    },
    {
        "title": "Source 2",
        "url": "https://example.edu/two",
        "snippet": "Beta",
        "verification_status": "UNCERTAIN",
    },
]


@contextlib.contextmanager
def _patch_research_tools(mock_llm: AsyncMock) -> Generator[None]:
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("packages.agents.llm.complete_json_chat", mock_llm))
        stack.enter_context(
            patch(
                "packages.agents.tools.web_search.web_search",
                AsyncMock(return_value=SEARCH_RESULTS),
            )
        )
        stack.enter_context(
            patch(
                "packages.agents.sub_agents.researcher.tools.web_fetch",
                AsyncMock(return_value="Fetched page content about photosynthesis."),
            )
        )
        yield


# ── ResearcherAgent ───────────────────────────────────────────────────────────

class TestResearcherAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_research_bundle(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        assert "research_bundle" in result
        bundle = ResearchBundle.model_validate(result["research_bundle"])
        assert bundle.topic == "Photosynthesis"
        assert len(bundle.sources) == 2

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        assert result["research_bundle"]["topic"] == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_parses_generic_code_fence(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_GENERIC_FENCE)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_parses_bare_json(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_JSON)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_invalid_json_returns_uncertain_source_candidates(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value="not json")
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        bundle = ResearchBundle.model_validate(result["research_bundle"])
        assert len(bundle.sources) >= 2
        assert all(source.verification_status == "UNCERTAIN" for source in bundle.sources)

    @pytest.mark.asyncio
    async def test_llm_error_returns_uncertain_sources(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(side_effect=RuntimeError("API timeout"))
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        bundle = ResearchBundle.model_validate(result["research_bundle"])
        assert len(bundle.sources) >= 2
        assert all(source.verification_status == "UNCERTAIN" for source in bundle.sources)

    @pytest.mark.asyncio
    async def test_too_few_sources_returns_uncertain_source_candidates(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        bad_bundle = json.dumps({
            "topic": "T",
            "sources": [{"title": "Only one", "credibility_score": 0.9, "verification_status": "VERIFIED"}],  # noqa: E501
        })
        mock_llm = _make_llm_mock(return_value=bad_bundle)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        bundle = ResearchBundle.model_validate(result["research_bundle"])
        assert len(bundle.sources) >= 2
        assert all(source.verification_status == "UNCERTAIN" for source in bundle.sources)

    @pytest.mark.asyncio
    async def test_missing_lesson_plan_uses_default_topic(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state(lesson_plan=None)))

        mock_llm.assert_awaited_once()
        assert "research_bundle" in result

    @pytest.mark.asyncio
    async def test_calls_llm_with_correct_model(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            await research_sources(cast("ResearcherState", _make_state()))

        assert mock_llm.call_args.kwargs["model"] == "4omc"

    @pytest.mark.asyncio
    async def test_metadata_tags_include_run_id(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            await research_sources(cast("ResearcherState", _make_state(run_id="run-abc")))

        tags = mock_llm.call_args.kwargs["tags"]
        assert any("run-abc" in t for t in tags)
        assert any("agent:researcher" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)

    @pytest.mark.asyncio
    async def test_research_policy_forwarded_to_prompt(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            await research_sources(cast("ResearcherState", _make_state(research_policy="rigorous")))

        user_msg = mock_llm.call_args.kwargs["messages"][1]["content"]
        assert "rigorous" in user_msg
        assert "Compact fetched evidence from 4omc.fetch" in user_msg
        assert "Fetched page content" in user_msg

    @pytest.mark.asyncio
    async def test_bundle_sources_have_verification_status(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node as research_sources

        mock_llm = _make_llm_mock(return_value=VALID_BUNDLE_WRAPPED)
        with _patch_research_tools(mock_llm):
            result = await research_sources(cast("ResearcherState", _make_state()))

        bundle = ResearchBundle.model_validate(result["research_bundle"])
        for source in bundle.sources:
            assert source.verification_status in ("VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN")


# ── Tools ─────────────────────────────────────────────────────────────────────

class TestResearcherTools:
    @pytest.mark.asyncio
    async def test_web_search_returns_results(self):
        from packages.agents.sub_agents.researcher.tools import web_search

        with patch(
            "packages.agents.sub_agents.researcher.tools.shared_web_search",
            AsyncMock(return_value=SEARCH_RESULTS),
        ):
            results = await web_search("photosynthesis", num_results=3)
        assert len(results) == 2
        assert all("title" in r for r in results)
        assert all("url" in r for r in results)
        assert all("snippet" in r for r in results)

    @pytest.mark.asyncio
    async def test_web_search_respects_num_results(self):
        from packages.agents.sub_agents.researcher.tools import web_search

        with patch(
            "packages.agents.sub_agents.researcher.tools.shared_web_search",
            AsyncMock(return_value=SEARCH_RESULTS),
        ):
            results = await web_search("test", num_results=5)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_web_fetch_returns_string(self):
        from packages.agents.sub_agents.researcher.tools import web_fetch

        with patch(
            "packages.agents.tools.ninerouter_web.NineRouterWebClient.fetch",
            AsyncMock(return_value=type("Fetch", (), {"content": "Example content"})()),
        ):
            content = await web_fetch("https://example.com")
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_web_fetch_includes_url(self):
        from packages.agents.sub_agents.researcher.tools import web_fetch

        with patch(
            "packages.agents.tools.ninerouter_web.NineRouterWebClient.fetch",
            AsyncMock(return_value=type("Fetch", (), {"content": "https://example.com/test"})()),
        ):
            content = await web_fetch("https://example.com/test")
        assert "example.com" in content


# ── Prompts ───────────────────────────────────────────────────────────────────

class TestResearcherPrompts:
    def test_prompt_contains_fact_protocol(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        researcher_system_prompt = load_system_prompt()

        assert "FACT" in researcher_system_prompt
        assert "Find" in researcher_system_prompt
        assert "Assess" in researcher_system_prompt
        assert "Cross-reference" in researcher_system_prompt
        assert "Tag" in researcher_system_prompt

    def test_prompt_contains_verification_statuses(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        researcher_system_prompt = load_system_prompt()

        for status in ("VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"):
            assert status in researcher_system_prompt

    def test_prompt_contains_research_policies(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        researcher_system_prompt = load_system_prompt()

        assert "basic" in researcher_system_prompt
        assert "standard" in researcher_system_prompt
        assert "rigorous" in researcher_system_prompt

    def test_prompt_contains_output_schema(self):
        from packages.agents.sub_agents.researcher.prompts import load_system_prompt
        researcher_system_prompt = load_system_prompt()

        assert "credibility_score" in researcher_system_prompt
        assert "verification_status" in researcher_system_prompt
