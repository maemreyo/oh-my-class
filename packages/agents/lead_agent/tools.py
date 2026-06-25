"""Lead Agent tools — thin @tool wrappers over compiled sub-agent graphs.

Each tool lazy-initialises its compiled graph (avoids re-compiling on every call).
The Lead Agent uses these tools to delegate work without managing sub-agent internals.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import tool

# Lazy-init compiled graphs — built once, reused across calls
_planner = None
_researcher = None
_creator = None
_reviewer = None


@tool
def run_planner(raw_request: str, class_info: dict[str, Any]) -> dict[str, Any]:
    """Design a lesson blueprint from the teacher's request and class info."""
    global _planner
    if _planner is None:
        from packages.agents.sub_agents.planner.agent import make_planner_agent
        _planner = make_planner_agent()

    result = asyncio.run(_planner.ainvoke({
        "messages": [],
        "raw_request": raw_request,
        "class_info": class_info,
        "run_id": "",
        "current_step": 3,
        "lesson_plan": None,
    }))
    return result.get("lesson_plan") or {}


@tool
def run_researcher(lesson_plan: dict[str, Any], research_policy: str = "standard") -> dict[str, Any]:  # noqa: E501
    """Research and synthesize sources for the lesson plan."""
    global _researcher
    if _researcher is None:
        from packages.agents.sub_agents.researcher.agent import make_researcher_agent
        _researcher = make_researcher_agent()

    result = asyncio.run(_researcher.ainvoke({
        "messages": [],
        "lesson_plan": lesson_plan,
        "research_policy": research_policy,
        "run_id": "",
        "current_step": 7,
        "research_bundle": None,
    }))
    return result.get("research_bundle") or {}


@tool
def run_content_creator(
    lesson_plan: dict[str, Any],
    research_bundle: dict[str, Any],
    artifact_types: list[str],
    theme: str = "default",
) -> list[dict[str, Any]]:
    """Generate lesson artifacts (lesson, worksheet, quiz, etc.)."""
    global _creator
    if _creator is None:
        from packages.agents.sub_agents.content_creator.agent import make_content_creator_agent
        _creator = make_content_creator_agent()

    result = asyncio.run(_creator.ainvoke({
        "messages": [],
        "lesson_plan": lesson_plan,
        "research_bundle": research_bundle,
        "artifact_types": artifact_types,
        "theme": theme,
        "run_id": "",
        "current_step": 8,
        "artifacts": None,
    }))
    return result.get("artifacts") or []


@tool
def run_reviewer(artifacts: list[dict[str, Any]], lesson_plan: dict[str, Any]) -> dict[str, Any]:
    """Review artifacts using G-Eval criteria. Returns quality scores and pass/fail."""
    global _reviewer
    if _reviewer is None:
        from packages.agents.sub_agents.reviewer.agent import make_reviewer_agent
        _reviewer = make_reviewer_agent()

    result = asyncio.run(_reviewer.ainvoke({
        "messages": [],
        "artifacts": artifacts,
        "lesson_plan": lesson_plan,
        "quality_scores": None,
        "quality_passed": None,
    }))
    return result.get("quality_scores") or {}


SUB_AGENT_TOOLS: list[Any] = [run_planner, run_researcher, run_content_creator, run_reviewer]
