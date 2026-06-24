"""Reviewer Agent — compiled graph factory and main pipeline adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from packages.agents.state import OhMyClassState


def make_reviewer_agent(checkpointer=None) -> "CompiledStateGraph":
    """Return a compiled LangGraph for the Reviewer Agent.

    Can be run standalone:
        agent = make_reviewer_agent()
        result = await agent.ainvoke({
            "messages": [], "artifacts": [...], "lesson_plan": {...},
            "quality_scores": None, "quality_passed": None,
        })
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.sub_agents.reviewer.nodes import reviewer_node
    from packages.agents.sub_agents.reviewer.state import ReviewerState

    builder = StateGraph(ReviewerState)
    builder.add_node("reviewer", reviewer_node)
    builder.set_entry_point("reviewer")
    builder.add_edge("reviewer", END)
    return builder.compile(checkpointer=checkpointer)


async def reviewer_graph_node(state: "OhMyClassState") -> dict[str, Any]:
    """Main pipeline graph node — adapter for the reviewer compiled sub-graph."""
    from packages.agents.sub_agents.reviewer.adapters import extract_reviewer_state
    from packages.agents.sub_agents.reviewer.nodes import reviewer_node

    reviewer_state = extract_reviewer_state(state)
    return await reviewer_node(reviewer_state)


async def quality_review(state: dict[str, Any]) -> dict[str, Any]:
    """Thin adapter: run the G-Eval quality review on state and return scores.

    Accepts any dict with optional 'artifacts', 'lesson_plan', 'run_id' keys.
    Returns {'quality_scores': {...}, 'quality_passed': bool}.
    """
    from packages.quality.layer4_judge.geval import GEvalScorer

    artifacts = state.get("artifacts") or []
    lesson_plan = state.get("lesson_plan")

    scorer = GEvalScorer()
    judge_output = await scorer.score(artifacts, lesson_plan=lesson_plan)

    return {
        "quality_scores": judge_output.model_dump() if hasattr(judge_output, "model_dump") else dict(judge_output),
        "quality_passed": bool(judge_output.passed),
    }
