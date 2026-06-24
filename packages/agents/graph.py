"""LangGraph graph builder for the oh-my-class pipeline.

Constructs the StateGraph with all 13 steps, conditional routing,
and interrupt() gates for teacher approval.
"""

from __future__ import annotations

from typing import Any

from packages.agents.gates import gate_01_blueprint_approval, gate_02_content_approval
from packages.agents.state import OhMyClassState


def _make_dummy_node(step: int, name: str):
    """Create a pass-through node for steps not yet wired to real agents."""
    async def dummy_node(state: OhMyClassState) -> dict[str, Any]:
        return {"current_step": step}
    dummy_node.__name__ = name
    return dummy_node


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
    from langgraph.graph import StateGraph, END
    from packages.agents.state import OhMyClassState
    from packages.agents.checkpointer import get_checkpointer

    if checkpointer is None:
        checkpointer = get_checkpointer(environment)

    graph = StateGraph(OhMyClassState)

    graph.add_node("step_01_preflight", _make_dummy_node(1, "preflight"))
    graph.add_node("step_02_quickstart", _make_dummy_node(2, "quickstart"))
    graph.add_node("step_03_blueprint", _make_dummy_node(3, "blueprint"))
    graph.add_node("gate_01_blueprint_approval", gate_01_blueprint_approval)
    graph.add_node("step_05_pack_scope", _make_dummy_node(5, "pack_scope"))
    graph.add_node("step_06_visual_engine", _make_dummy_node(6, "visual_engine"))
    graph.add_node("step_07_research", _make_dummy_node(7, "research"))
    graph.add_node("step_08_generate", _make_dummy_node(8, "generate"))
    graph.add_node("step_09_import", _make_dummy_node(9, "import"))
    graph.add_node("step_10_review", _make_dummy_node(10, "review"))
    graph.add_node("gate_02_content_approval", gate_02_content_approval)
    graph.add_node("step_12_validate", _make_dummy_node(12, "validate"))
    graph.add_node("step_13_export", _make_dummy_node(13, "export"))

    graph.set_entry_point("step_01_preflight")
    graph.add_edge("step_01_preflight", "step_02_quickstart")
    graph.add_edge("step_02_quickstart", "step_03_blueprint")
    graph.add_edge("step_03_blueprint", "gate_01_blueprint_approval")

    graph.add_conditional_edges(
        "gate_01_blueprint_approval",
        route_after_blueprint_gate,
        {
            "approve": "step_05_pack_scope",
            "reject": "step_03_blueprint",
        },
    )

    graph.add_edge("step_05_pack_scope", "step_06_visual_engine")
    graph.add_edge("step_06_visual_engine", "step_07_research")
    graph.add_edge("step_07_research", "step_08_generate")
    graph.add_edge("step_08_generate", "step_09_import")
    graph.add_edge("step_09_import", "step_10_review")

    graph.add_conditional_edges(
        "step_10_review",
        route_after_review,
        {
            "human_review": "gate_02_content_approval",
            "escalate": END,
            "repair": "step_08_generate",
        },
    )

    graph.add_conditional_edges(
        "gate_02_content_approval",
        route_after_content_gate,
        {
            "approve": "step_12_validate",
            "reject": "step_08_generate",
        },
    )

    graph.add_edge("step_12_validate", "step_13_export")
    graph.add_edge("step_13_export", END)

    return graph.compile(checkpointer=checkpointer)


def route_after_blueprint_gate(state: OhMyClassState) -> str:
    """Route after Gate 01 (blueprint approval).

    approve/edit → proceed to pack scope; reject → re-run planner.
    """
    decision = state.get("teacher_decision", "approve")
    return "approve" if decision in ("approve", "edit") else "reject"


def route_after_content_gate(state: OhMyClassState) -> str:
    """Route after Gate 02 (content approval).

    approve → finalize; reject → regenerate artifacts.
    """
    decision = state.get("teacher_decision", "approve")
    return "approve" if decision == "approve" else "reject"


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
