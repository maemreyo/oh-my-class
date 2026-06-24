"""Tests for Lead Agent — make_lead_agent(), recovery, prompt loading."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── make_lead_agent ────────────────────────────────────────────────────────────

def test_make_lead_agent_returns_compiled_graph():
    with patch("packages.agents.lead_agent.agent.ChatOpenAI"):
        from packages.agents.lead_agent.agent import make_lead_agent
        agent = make_lead_agent()
    assert agent is not None
    assert hasattr(agent, "invoke")
    assert hasattr(agent, "ainvoke")


def test_make_lead_agent_accepts_model_override():
    mock_model = MagicMock()
    with patch("packages.agents.lead_agent.agent.ChatOpenAI"):
        from packages.agents.lead_agent.agent import make_lead_agent
        agent = make_lead_agent(model=mock_model)
    assert agent is not None


def test_make_lead_agent_accepts_tools_override():
    from langchain_core.tools import tool

    @tool
    def dummy_tool(x: str) -> str:
        """A dummy tool."""
        return x

    with patch("packages.agents.lead_agent.agent.ChatOpenAI"):
        from packages.agents.lead_agent.agent import make_lead_agent
        agent = make_lead_agent(tools=[dummy_tool])
    assert agent is not None


def test_make_lead_agent_is_create_react_agent():
    """make_lead_agent() must use create_react_agent (B2 pattern)."""
    with patch("packages.agents.lead_agent.agent.ChatOpenAI"), \
         patch("packages.agents.lead_agent.agent.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(invoke=lambda x: x)
        from packages.agents.lead_agent.agent import make_lead_agent
        make_lead_agent()
    mock_create.assert_called_once()


# ── system prompt ──────────────────────────────────────────────────────────────

def test_system_prompt_loads():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_system_prompt_contains_lead_agent_reference():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert "Lead Agent" in prompt


def test_system_prompt_mentions_run_planner():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert "run_planner" in prompt


def test_system_prompt_mentions_recovery():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert "Recovery" in prompt or "recovery" in prompt


def test_system_prompt_loaded_from_file_not_hardcoded():
    """Prompt must come from a .md file, not a hardcoded string in agent.py."""
    import inspect
    from packages.agents.lead_agent import agent as agent_module
    source = inspect.getsource(agent_module)
    assert "run_planner" not in source or "load_system_prompt" in source


# ── recovery ───────────────────────────────────────────────────────────────────

def test_build_recovery_context_includes_score():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {
        "overall_score": 5.5,
        "feedback": "Content too abstract for Grade 3.",
        "per_artifact": {"lesson": {"overall": 5.0}},
    }
    ctx = build_recovery_context(review, revision_count=1)
    assert "5.5" in ctx


def test_build_recovery_context_includes_feedback():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {
        "overall_score": 5.5,
        "feedback": "Content too abstract for Grade 3.",
        "per_artifact": {"lesson": {"overall": 5.0}},
    }
    ctx = build_recovery_context(review, revision_count=1)
    assert "Content too abstract" in ctx


def test_build_recovery_context_identifies_weak_artifacts():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {
        "overall_score": 6.0,
        "feedback": "Worksheet is too hard.",
        "per_artifact": {
            "lesson": {"overall": 8.5},
            "worksheet": {"overall": 4.0},
        },
    }
    ctx = build_recovery_context(review, revision_count=2)
    assert "worksheet" in ctx


def test_build_recovery_context_excludes_passing_artifacts():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {
        "overall_score": 6.0,
        "feedback": "Worksheet is too hard.",
        "per_artifact": {
            "lesson": {"overall": 8.5},
            "worksheet": {"overall": 4.0},
        },
    }
    ctx = build_recovery_context(review, revision_count=2)
    weak_section = ctx.split("Weak artifacts")[-1] if "Weak artifacts" in ctx else ctx
    assert "lesson" not in weak_section.split("\n")[0]


def test_build_recovery_context_includes_revision_count():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {"overall_score": 5.0, "feedback": "Too brief.", "per_artifact": {}}
    ctx = build_recovery_context(review, revision_count=2)
    assert "2" in ctx


def test_build_recovery_context_handles_missing_feedback():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {"overall_score": 4.0, "per_artifact": {}}
    ctx = build_recovery_context(review, revision_count=1)
    assert isinstance(ctx, str)
    assert len(ctx) > 0


def test_build_recovery_context_handles_empty_per_artifact():
    from packages.agents.lead_agent.recovery import build_recovery_context
    review = {"overall_score": 5.0, "feedback": "Needs work.", "per_artifact": {}}
    ctx = build_recovery_context(review, revision_count=1)
    assert "5.0" in ctx


# ── node.py — graph adapter ────────────────────────────────────────────────────

def test_lead_agent_node_is_importable():
    from packages.agents.lead_agent.node import lead_agent_node  # noqa: F401


def test_lead_agent_node_is_async():
    import asyncio
    import inspect
    from packages.agents.lead_agent.node import lead_agent_node
    assert inspect.iscoroutinefunction(lead_agent_node)


def test_lead_agent_node_injects_recovery_on_retry():
    """When revision_count > 0 and review_results present, recovery context is injected."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from packages.agents.lead_agent.node import lead_agent_node

    state = {
        "raw_request": "Teach fractions to Grade 4",
        "class_info": {"grade": 4, "subject": "math"},
        "run_id": "test-run",
        "current_step": 10,
        "revision_count": 1,
        "review_results": {
            "overall_score": 5.5,
            "feedback": "Too hard.",
            "per_artifact": {"worksheet": {"overall": 5.0}},
        },
        "lesson_plan": {"title": "Fractions"},
        "research_bundle": {},
        "artifacts": [],
    }

    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [],
        "task": "",
        "context": {},
        "result": None,
        "recovery_guidance": None,
    }

    with patch("packages.agents.lead_agent.node._lead_agent", mock_agent):
        result = asyncio.run(lead_agent_node(state))

    call_args = mock_agent.invoke.call_args[0][0]
    messages = call_args["messages"]
    assert any("Recovery" in str(m) or "recovery" in str(m).lower() for m in messages)


# ── module structure ───────────────────────────────────────────────────────────

def test_recovery_py_exists():
    from packages.agents.lead_agent import recovery  # noqa: F401


def test_node_py_exists():
    from packages.agents.lead_agent import node  # noqa: F401


def test_prompts_package_exists():
    from packages.agents.lead_agent import prompts  # noqa: F401


def test_tools_sub_agent_tools_list():
    from packages.agents.lead_agent.tools import SUB_AGENT_TOOLS
    assert len(SUB_AGENT_TOOLS) == 4
