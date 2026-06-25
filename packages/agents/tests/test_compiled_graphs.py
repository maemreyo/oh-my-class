"""Tests for C2 compiled sub-agent graphs.

Each agent must be invocable standalone as a compiled LangGraph graph,
independent from the main pipeline graph.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


def _make_litellm_mock(content: str) -> MagicMock:
    mock_module = MagicMock()
    mock_module.acompletion = AsyncMock(return_value=_make_mock_response(content))
    return mock_module


VALID_PLAN = json.dumps({
    "topic": "Photosynthesis",
    "grade_level": "Grade 5",
    "subject": "science",
    "duration_minutes": 45,
    "learning_objectives": [
        {"description": "Understand photosynthesis", "bloom_level": "understand"},
        {"description": "Apply knowledge", "bloom_level": "apply"},
    ],
})

VALID_BUNDLE = json.dumps({
    "topic": "Photosynthesis",
    "sources": [
        {"title": "S1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
        {"title": "S2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
    ],
})

VALID_ARTIFACTS = json.dumps([{
    "artifact_type": "lesson",
    "theme": "default",
    "title": "Photosynthesis Lesson",
    "sections": [{"title": "Intro", "content": "Plants make food."}],
    "metadata": {},
    "accessibility": {"language": "vi", "alt_texts": {}},
}])


# ── make_*_agent factories ─────────────────────────────────────────────────────

class TestPlannerAgentFactory:
    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from packages.agents.sub_agents.planner.agent import make_planner_agent

        agent = make_planner_agent()
        assert isinstance(agent, CompiledStateGraph)

    def test_compiled_graph_without_checkpointer(self):
        from packages.agents.sub_agents.planner.agent import make_planner_agent

        agent = make_planner_agent(checkpointer=None)
        assert agent is not None

    @pytest.mark.asyncio
    async def test_ainvoke_returns_lesson_plan(self):
        from packages.agents.sub_agents.planner.agent import make_planner_agent

        mock_litellm = _make_litellm_mock(VALID_PLAN)
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            agent = make_planner_agent()
            result = await agent.ainvoke({
                "messages": [],
                "raw_request": "Teach photosynthesis to Grade 5",
                "class_info": {"grade": 5, "subject": "science"},
                "run_id": "test-001",
                "current_step": 3,
                "lesson_plan": None,
            })

        assert "lesson_plan" in result
        assert result["lesson_plan"]["topic"] == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_standalone_without_main_graph(self):
        """Planner can run without importing OhMyClassState or graph.py."""
        from packages.agents.sub_agents.planner.agent import make_planner_agent

        mock_litellm = _make_litellm_mock(VALID_PLAN)
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            agent = make_planner_agent()
            result = await agent.ainvoke({
                "messages": [],
                "raw_request": "Teach fractions to Grade 3",
                "class_info": {"grade": 3, "subject": "math"},
                "run_id": "standalone-test",
                "current_step": 3,
                "lesson_plan": None,
            })

        assert result["lesson_plan"] is not None


class TestResearcherAgentFactory:
    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from packages.agents.sub_agents.researcher.agent import make_researcher_agent

        agent = make_researcher_agent()
        assert isinstance(agent, CompiledStateGraph)

    @pytest.mark.asyncio
    async def test_ainvoke_returns_research_bundle(self):
        from packages.agents.sub_agents.researcher.agent import make_researcher_agent

        mock_litellm = _make_litellm_mock(VALID_BUNDLE)
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            agent = make_researcher_agent()
            result = await agent.ainvoke({
                "messages": [],
                "lesson_plan": {"topic": "Photosynthesis"},
                "research_policy": "standard",
                "run_id": "test-001",
                "current_step": 7,
                "research_bundle": None,
            })

        assert "research_bundle" in result
        assert result["research_bundle"]["topic"] == "Photosynthesis"


class TestContentCreatorAgentFactory:
    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from packages.agents.sub_agents.content_creator.agent import make_content_creator_agent

        agent = make_content_creator_agent()
        assert isinstance(agent, CompiledStateGraph)

    @pytest.mark.asyncio
    async def test_ainvoke_returns_artifacts(self):
        from packages.agents.sub_agents.content_creator.agent import make_content_creator_agent

        mock_litellm = _make_litellm_mock(VALID_ARTIFACTS)
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            agent = make_content_creator_agent()
            result = await agent.ainvoke({
                "messages": [],
                "lesson_plan": {"topic": "Photosynthesis"},
                "research_bundle": {"topic": "Photosynthesis", "sources": []},
                "artifact_types": ["lesson"],
                "theme": "default",
                "run_id": "test-001",
                "current_step": 8,
                "artifacts": None,
            })

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1


class TestReviewerAgentFactory:
    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from packages.agents.sub_agents.reviewer.agent import make_reviewer_agent

        agent = make_reviewer_agent()
        assert isinstance(agent, CompiledStateGraph)


# ── nodes.py independence ──────────────────────────────────────────────────────

class TestNodesModuleExists:
    def test_planner_nodes_importable(self):
        from packages.agents.sub_agents.planner.nodes import planner_node
        assert callable(planner_node)

    def test_researcher_nodes_importable(self):
        from packages.agents.sub_agents.researcher.nodes import researcher_node
        assert callable(researcher_node)

    def test_content_creator_nodes_importable(self):
        from packages.agents.sub_agents.content_creator.nodes import content_creator_node
        assert callable(content_creator_node)

    def test_reviewer_nodes_importable(self):
        from packages.agents.sub_agents.reviewer.nodes import reviewer_node
        assert callable(reviewer_node)


# ── lead_agent/tools.py ────────────────────────────────────────────────────────

class TestLeadAgentTools:
    def test_run_planner_is_tool(self):
        from langchain_core.tools import BaseTool

        from packages.agents.lead_agent.tools import run_planner

        assert isinstance(run_planner, BaseTool)

    def test_run_researcher_is_tool(self):
        from langchain_core.tools import BaseTool

        from packages.agents.lead_agent.tools import run_researcher

        assert isinstance(run_researcher, BaseTool)

    def test_run_content_creator_is_tool(self):
        from langchain_core.tools import BaseTool

        from packages.agents.lead_agent.tools import run_content_creator

        assert isinstance(run_content_creator, BaseTool)

    def test_run_reviewer_is_tool(self):
        from langchain_core.tools import BaseTool

        from packages.agents.lead_agent.tools import run_reviewer

        assert isinstance(run_reviewer, BaseTool)

    def test_tools_list_exports_all_four(self):
        from packages.agents.lead_agent.tools import SUB_AGENT_TOOLS

        assert len(SUB_AGENT_TOOLS) == 4
        names = {t.name for t in SUB_AGENT_TOOLS}
        assert "run_planner" in names
        assert "run_researcher" in names
        assert "run_content_creator" in names
        assert "run_reviewer" in names
