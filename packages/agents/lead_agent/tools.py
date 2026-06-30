"""Lead Agent tools — thin @tool wrappers over compiled sub-agent graphs.

Each tool lazy-initialises its compiled graph (avoids re-compiling on every call).
The Lead Agent uses these tools to delegate work without managing sub-agent internals.
"""

from __future__ import annotations

import anyio
from typing import Any

from langchain_core.tools import tool

@tool  # pyright: ignore[reportUntypedFunctionDecorator]
def run_planner(raw_request: str, class_info: dict[str, Any]) -> dict[str, Any]:
    """Design a lesson blueprint from the teacher's request and class info."""
    from packages.agents.sub_agents.planner.nodes import planner_node

    result = anyio.run(planner_node, {
        "messages": [],
        "raw_request": raw_request,
        "class_info": class_info,
        "run_id": "",
        "current_step": 3,
        "lesson_plan": None,
    })
    return result.get("lesson_plan") or {}


@tool  # pyright: ignore[reportUntypedFunctionDecorator]
def run_researcher(lesson_plan: dict[str, Any], research_policy: str = "standard") -> dict[str, Any]:  # noqa: E501
    """Research and synthesize sources for the lesson plan."""
    from packages.agents.sub_agents.researcher.nodes import researcher_node

    result = anyio.run(researcher_node, {
        "messages": [],
        "lesson_plan": lesson_plan,
        "research_policy": research_policy,
        "run_id": "",
        "current_step": 7,
        "research_bundle": None,
    })
    return result.get("research_bundle") or {}


@tool  # pyright: ignore[reportUntypedFunctionDecorator]
def run_content_creator(
    lesson_plan: dict[str, Any],
    research_bundle: dict[str, Any],
    artifact_types: list[str],
    theme: str = "default",
) -> list[dict[str, Any]]:
    """Generate lesson artifacts (lesson, worksheet, quiz, etc.)."""
    from packages.agents.sub_agents.content_creator.nodes import content_creator_node

    result = anyio.run(content_creator_node, {
        "messages": [],
        "lesson_plan": lesson_plan,
        "research_bundle": research_bundle,
        "artifact_types": artifact_types,
        "theme": theme,
        "run_id": "",
        "current_step": 8,
        "artifacts": None,
    })
    return result.get("artifacts") or []


@tool  # pyright: ignore[reportUntypedFunctionDecorator]
def run_reviewer(artifacts: list[dict[str, Any]], lesson_plan: dict[str, Any]) -> dict[str, Any]:
    """Review artifacts using G-Eval criteria. Returns quality scores and pass/fail."""
    from packages.agents.sub_agents.reviewer.nodes import reviewer_node

    result = anyio.run(reviewer_node, {
        "messages": [],
        "artifacts": artifacts,
        "lesson_plan": lesson_plan,
        "quality_scores": None,
        "quality_passed": None,
    })
    return result.get("quality_scores") or {}


SUB_AGENT_TOOLS: list[Any] = [run_planner, run_researcher, run_content_creator, run_reviewer]
