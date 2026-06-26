"""LangGraph graph builder for the oh-my-class pipeline.

Constructs the StateGraph with all 18 nodes, quality gate chain,
healing orchestrator, and interrupt() gates for teacher approval.
"""

from __future__ import annotations

import asyncio
import inspect
import time as _time
from typing import Any

from packages.agents.events import emit_run_event

from packages.agents.gates import (
    gate_01_blueprint_approval,
    gate_02_content_approval,
    step_09_schema_validate,
    step_10_content_review,
    step_10b_llm_judge,
    step_11_export_readiness,
)
from packages.agents.healing import healing_node, route_after_healing
from packages.agents.nodes.finalize import step_12_finalize
from packages.agents.nodes.pack_scope import step_05_pack_scope
from packages.agents.nodes.preflight import step_01_preflight
from packages.agents.nodes.quickstart import step_02_quickstart
from packages.agents.nodes.visual_engine import step_06_visual_engine
from packages.agents.state import (
    OhMyClassState,  # noqa: TC001  needed at runtime for LangGraph get_type_hints
)
from packages.agents.sub_agents.content_creator.agent import content_creator_graph_node
from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node
from packages.agents.sub_agents.planner.agent import planner_graph_node
from packages.agents.sub_agents.researcher.agent import researcher_graph_node
from packages.agents.sub_agents.roadmap_agent.agent import roadmap_graph_node


def _wrap_node(node_fn, node_name: str, agent_name: str = ""):
    """Wrap a LangGraph node with step_started/completed/failed events."""
    _is_async = inspect.iscoroutinefunction(node_fn)

    async def wrapped(state: OhMyClassState) -> dict[str, Any]:
        run_id = str(state.get("run_id", ""))
        emit_run_event(run_id, "step_started", {
            "node": node_name,
            "agent": agent_name,
        })
        started = _time.monotonic()
        try:
            if _is_async:
                result = await node_fn(state)
            else:
                result = await asyncio.to_thread(node_fn, state)
            duration = round(_time.monotonic() - started, 1)
            result_keys = list(result.keys()) if isinstance(result, dict) else []
            emit_run_event(run_id, "step_completed", {
                "node": node_name,
                "agent": agent_name,
                "duration_s": duration,
                "result_keys": result_keys,
            })
            return result
        except Exception as exc:
            duration = round(_time.monotonic() - started, 1)
            emit_run_event(run_id, "step_failed", {
                "node": node_name,
                "agent": agent_name,
                "duration_s": duration,
                "error": str(exc)[:200],
                "error_type": type(exc).__name__,
            })
            raise

    wrapped.__name__ = node_name
    return wrapped


def _make_dummy_node(step: int, name: str):
    """Create a pass-through node for steps not yet wired to real agents."""
    async def dummy_node(state: OhMyClassState) -> dict[str, Any]:
        return {"current_step": step}
    dummy_node.__name__ = name
    return dummy_node


def escalate_node(state: OhMyClassState) -> dict[str, Any]:
    """Terminal node for escalated failures — marks run as failed."""
    return {
        "error": state.get("escalate_reason") or state.get("error") or "Escalated",
        "escalate": True,
    }


def build_oh_my_class_graph(
    *,
    environment: str = "development",
    checkpointer: Any | None = None,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
) -> Any:
    """Build and compile the oh-my-class LangGraph pipeline.

    Creates a StateGraph with 16 nodes: 12 pipeline steps, 2 HITL gates,
    healing_node, and escalate_node.

    Pipeline steps:
        01. Preflight — validate raw teacher input
        02. Quickstart — initialize run, create thread/dirs/metadata
        03. Blueprint — Planner Agent → LessonPlan JSON
        04. Gate 1 — interrupt() for blueprint approval
        05. Pack Scope — determine artifact types
        06. Visual Engine — choose theme/layout/visual treatments
        07. Research — Researcher Agent → ResearchBundle JSON
        08. Generate — ContentCreator Agent → ArtifactContent[] JSON
        09. Schema Validate — Layer 1: Pydantic schema check
        10. Content Review — Layer 2-3: fact-check, HTML, age, answer-key
        10b. LLM Judge — Layer 4: G-Eval scoring
        11. Gate 2 — interrupt() for content approval
        12. Export Readiness — Layer 6: pre-export validation
        13. Finalize — package to requested format(s) and persist
        H. Healing Node — select + apply recovery strategy
        E. Escalate Node — terminal failure node
    """
    from langgraph.graph import END, StateGraph

    from packages.agents.checkpointer import get_checkpointer
    from packages.agents.state import OhMyClassState

    if checkpointer is None:
        checkpointer = get_checkpointer(environment)

    graph = StateGraph(OhMyClassState)

    # ── Pipeline nodes ─────────────────────────────────────────────────────────
    graph.add_node("step_00_diagnostic", _wrap_node(diagnostician_graph_node, "step_00_diagnostic", "diagnostician"))
    graph.add_node("step_01_preflight", _wrap_node(step_01_preflight, "step_01_preflight"))
    graph.add_node("step_02_quickstart", _wrap_node(step_02_quickstart, "step_02_quickstart"))
    graph.add_node("step_03_blueprint", _wrap_node(planner_graph_node, "step_03_blueprint", "planner"))
    graph.add_node("gate_01_blueprint_approval", _wrap_node(gate_01_blueprint_approval, "gate_01_blueprint_approval"))
    graph.add_node("step_04b_roadmap", _wrap_node(roadmap_graph_node, "step_04b_roadmap", "roadmap"))
    graph.add_node("step_05_pack_scope", _wrap_node(step_05_pack_scope, "step_05_pack_scope"))
    graph.add_node("step_06_visual_engine", _wrap_node(step_06_visual_engine, "step_06_visual_engine"))
    graph.add_node("step_07_research", _wrap_node(researcher_graph_node, "step_07_research", "researcher"))
    graph.add_node("step_08_generate", _wrap_node(content_creator_graph_node, "step_08_generate", "content_creator"))
    graph.add_node("step_09_schema_validate", _wrap_node(step_09_schema_validate, "step_09_schema_validate"))
    graph.add_node("step_10_content_review", _wrap_node(step_10_content_review, "step_10_content_review"))
    graph.add_node("step_10b_llm_judge", _wrap_node(step_10b_llm_judge, "step_10b_llm_judge"))
    graph.add_node("gate_02_content_approval", _wrap_node(gate_02_content_approval, "gate_02_content_approval"))
    graph.add_node("step_11_export_readiness", _wrap_node(step_11_export_readiness, "step_11_export_readiness"))
    graph.add_node("step_12_finalize", _wrap_node(step_12_finalize, "step_12_finalize"))
    graph.add_node("healing_node", _wrap_node(healing_node, "healing_node", "healing"))
    graph.add_node("escalate_node", _wrap_node(escalate_node, "escalate_node"))

    # ── Edges ──────────────────────────────────────────────────────────────────
    graph.set_entry_point("step_00_diagnostic")
    graph.add_conditional_edges(
        "step_00_diagnostic",
        route_after_diagnostic,
        {
            "step_01_preflight": "step_01_preflight",
        },
    )
    graph.add_edge("step_01_preflight", "step_02_quickstart")
    graph.add_edge("step_02_quickstart", "step_03_blueprint")
    graph.add_edge("step_03_blueprint", "gate_01_blueprint_approval")

    graph.add_conditional_edges(
        "gate_01_blueprint_approval",
        route_after_blueprint_gate,
        {
            "approve": "step_04b_roadmap",
            "reject": "step_03_blueprint",
        },
    )

    graph.add_conditional_edges(
        "step_04b_roadmap",
        route_after_roadmap,
        {
            "step_05_pack_scope": "step_05_pack_scope",
        },
    )

    graph.add_edge("step_05_pack_scope", "step_06_visual_engine")
    graph.add_edge("step_06_visual_engine", "step_07_research")
    graph.add_edge("step_07_research", "step_08_generate")
    graph.add_edge("step_08_generate", "step_09_schema_validate")

    graph.add_conditional_edges(
        "step_09_schema_validate",
        route_after_schema,
        {
            "step_10_content_review": "step_10_content_review",
            "healing_node": "healing_node",
        },
    )

    graph.add_conditional_edges(
        "step_10_content_review",
        route_after_content_review,
        {
            "step_10b_llm_judge": "step_10b_llm_judge",
            "healing_node": "healing_node",
        },
    )

    graph.add_conditional_edges(
        "step_10b_llm_judge",
        route_after_judge,
        {
            "gate_02_content_approval": "gate_02_content_approval",
            "healing_node": "healing_node",
        },
    )

    graph.add_conditional_edges(
        "gate_02_content_approval",
        route_after_content_gate,
        {
            "approve": "step_11_export_readiness",
            "reject": "step_08_generate",
        },
    )

    graph.add_conditional_edges(
        "step_11_export_readiness",
        route_after_export,
        {
            "step_12_finalize": "step_12_finalize",
            "escalate_node": "escalate_node",
        },
    )

    graph.add_conditional_edges(
        "healing_node",
        route_after_healing,
        {
            "step_08_generate": "step_08_generate",
            "escalate_node": "escalate_node",
        },
    )

    graph.add_edge("step_12_finalize", END)
    graph.add_edge("escalate_node", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
    )


# ── Router functions ────────────────────────────────────────────────────────────

def route_after_diagnostic(state: OhMyClassState) -> str:
    """Always proceed to preflight — skip logic lives inside diagnostician_graph_node."""
    return "step_01_preflight"


def route_after_roadmap(state: OhMyClassState) -> str:
    """Always proceed to pack_scope — skip logic lives inside roadmap_graph_node."""
    return "step_05_pack_scope"


def route_after_blueprint_gate(state: OhMyClassState) -> str:
    """Route after Gate 01: approve/edit → pack scope; reject → re-run planner."""
    decision = state.get("teacher_decision", "approve")
    return "approve" if decision in ("approve", "edit") else "reject"


def route_after_content_gate(state: OhMyClassState) -> str:
    """Route after Gate 02: approve → export readiness; reject → regenerate."""
    decision = state.get("teacher_decision", "approve")
    return "approve" if decision == "approve" else "reject"


def route_after_schema(state: OhMyClassState) -> str:
    """Route after schema validation: pass → content review; fail → healing."""
    return "step_10_content_review" if state.get("schema_valid") else "healing_node"


def route_after_content_review(state: OhMyClassState) -> str:
    """Route after content review: pass → LLM judge; fail → healing."""
    return "step_10b_llm_judge" if state.get("content_review_passed") else "healing_node"


def route_after_judge(state: OhMyClassState) -> str:
    """Route after LLM judge: score ≥ 7.0 → gate 02; below → healing."""
    score = state.get("judge_score", 0.0) or 0.0
    return "gate_02_content_approval" if score >= 7.0 else "healing_node"


def route_after_export(state: OhMyClassState) -> str:
    """Route after export readiness: pass → finalize; fail → escalate."""
    return "step_12_finalize" if state.get("export_ready") else "escalate_node"


# ── Legacy router functions (kept for test compatibility) ───────────────────────

def route_after_review(state: OhMyClassState) -> str:
    """Legacy: route after quality review node (pre-quality-gate-nodes)."""
    scores = state.get("quality_scores", {})
    overall = scores.get("overall", 0.0) if scores else 0.0
    if overall >= 7.0:
        return "human_review"
    if state.get("revision_count", 0) >= 3:
        return "escalate"
    return "repair"


def route_after_human_review(state: OhMyClassState) -> str:
    """Legacy: route after teacher gate 2 (pre-quality-gate-nodes)."""
    return "validate" if state.get("teacher_approved", False) else "generate"
