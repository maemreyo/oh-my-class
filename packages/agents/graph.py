"""LangGraph graph builder for the oh-my-class pipeline.

Constructs the StateGraph with all 13 steps, conditional routing,
and interrupt() gates for teacher approval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def build_oh_my_class_graph(
    *,
    environment: str = "development",
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the oh-my-class LangGraph pipeline.

    Creates a StateGraph with 13 sequential steps, two interrupt() gates
    (blueprint approval at Step 04, content approval at Step 11), and
    conditional routing for the quality review loop.

    Args:
        environment: One of 'development', 'staging', 'production'.
        checkpointer: Pre-configured checkpointer instance. If None,
            uses get_checkpointer() with the given environment.

    Returns:
        Compiled LangGraph graph ready for invocation.

    Pipeline steps:
        01. Preflight — validate raw teacher input
        02. Quickstart — initialize run, create thread/dirs/metadata
        03. Blueprint — Planner Agent → LessonPlan JSON
        04. Teacher Gate 1 — interrupt() for blueprint approval
        05. Pack Scope — determine artifact types
        06. Visual Engine — choose theme/layout/visual treatments
        07. Research — Researcher Agent → ResearchBundle JSON
        08. Generate — ContentCreator Agent → ArtifactContent[] JSON
        09. Import — assemble raw artifacts; run Layer 1–3 gates
        10. Review — LLM-as-Judge (Layer 4); self-heal loop
        11. Teacher Gate 2 — interrupt() for content approval
        12. Validate — Layer 6 multi-judge; schema + contract check
        13. Export — package to requested format(s) and persist
    """
    # TODO: Implement with langgraph.StateGraph
    # from langgraph.graph import StateGraph
    # graph = StateGraph(OhMyClassState)
    # Add nodes, edges, conditional edges, interrupt points
    # return graph.compile(checkpointer=checkpointer)
    raise NotImplementedError("build_oh_my_class_graph() stub — implement with LangGraph")


def route_after_review(state: OhMyClassState) -> str:
    """Route after quality review (Step 10).

    Returns:
        'human_review' if score >= 7.0, 'escalate' if revision_count >= 3,
        'repair' otherwise.
    """
    scores = state.get("quality_scores", {})
    overall = scores.get("overall", 0.0) if scores else 0.0
    if overall >= 7.0:
        return "human_review"
    if state.get("revision_count", 0) >= 3:
        return "escalate"
    return "repair"


def route_after_human_review(state: OhMyClassState) -> str:
    """Route after teacher gate 2 (Step 11).

    Returns:
        'validate' if teacher approved, 'generate' to loop back.
    """
    return "validate" if state.get("teacher_approved", False) else "generate"
