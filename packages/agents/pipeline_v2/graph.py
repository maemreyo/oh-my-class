"""Pipeline V2 stage graph skeleton."""

from __future__ import annotations

from typing import Literal

from packages.agents.pipeline_v2.nodes import PipelineV2State, make_stage_node
from packages.agents.pipeline_v2.stages import PIPELINE_V2_STAGES

InterruptSpec = list[str] | Literal["*"] | None
type LangGraphRunnableConfig = dict[str, dict[str, str]]


def build_pipeline_v2_graph(
    *,
    checkpointer=None,
    interrupt_before: InterruptSpec = None,
    interrupt_after: InterruptSpec = None,
):
    """Build the Pipeline V2 stage graph without initializing external clients."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(PipelineV2State)
    for stage in PIPELINE_V2_STAGES:
        graph.add_node(stage.value, make_stage_node(stage))

    first_stage = PIPELINE_V2_STAGES[0]
    graph.set_entry_point(first_stage.value)

    previous = first_stage
    for stage in PIPELINE_V2_STAGES[1:]:
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


def pipeline_v2_thread_config(run_id: str) -> LangGraphRunnableConfig:
    return {"configurable": {"thread_id": run_id}}
