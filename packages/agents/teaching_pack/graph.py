"""Teaching Pack stage graph skeleton."""

from __future__ import annotations

from typing import Literal

from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    make_stage_node,
    route_after_teacher_approval,
)
from packages.agents.teaching_pack.quality_routing import route_after_render_quality
from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage

InterruptSpec = list[str] | Literal["*"] | None
type LangGraphRunnableConfig = dict[str, dict[str, str]]


def build_teaching_pack_graph(
    *,
    checkpointer=None,
    interrupt_before: InterruptSpec = None,
    interrupt_after: InterruptSpec = None,
):
    """Build the Teaching Pack stage graph without initializing external clients."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(TeachingPackState)
    for stage in TEACHING_PACK_STAGES:
        graph.add_node(stage.value, make_stage_node(stage))

    first_stage = TEACHING_PACK_STAGES[0]
    graph.set_entry_point(first_stage.value)

    previous = first_stage
    for stage in TEACHING_PACK_STAGES[1:]:
        if previous is TeachingPackStage.TEACHER_APPROVAL:
            graph.add_conditional_edges(
                previous.value,
                route_after_teacher_approval,
                {
                    TeachingPackStage.ARTIFACT_WORKFLOW.value: TeachingPackStage.ARTIFACT_WORKFLOW.value,
                    TeachingPackStage.EXPORT_FINALIZE.value: TeachingPackStage.EXPORT_FINALIZE.value,
                },
            )
        elif previous is TeachingPackStage.RENDER_QUALITY:
            graph.add_conditional_edges(
                previous.value,
                route_after_render_quality,
                {
                    TeachingPackStage.PLANNING_BLUEPRINT.value: TeachingPackStage.PLANNING_BLUEPRINT.value,
                    TeachingPackStage.POST_BLUEPRINT_RESEARCH.value: TeachingPackStage.POST_BLUEPRINT_RESEARCH.value,
                    TeachingPackStage.ARTIFACT_WORKFLOW.value: TeachingPackStage.ARTIFACT_WORKFLOW.value,
                    TeachingPackStage.TEACHER_APPROVAL.value: TeachingPackStage.TEACHER_APPROVAL.value,
                },
            )
        else:
            graph.add_edge(previous.value, stage.value)
        previous = stage
    graph.add_edge(previous.value, END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=_normalize_interrupts(interrupt_before),
        interrupt_after=_normalize_interrupts(interrupt_after),
    )


def _normalize_interrupts(interrupts: InterruptSpec) -> InterruptSpec:
    match interrupts:
        case None:
            return None
        case "*":
            return "*"
        case list() as values:
            return values


def teaching_pack_thread_config(run_id: str) -> LangGraphRunnableConfig:
    return {"configurable": {"thread_id": run_id}}
