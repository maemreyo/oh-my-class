"""Teaching Pack stage graph skeleton."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    make_stage_node,
    route_after_compliance_gate,
    route_after_triage,
    route_after_unit_approval,
    route_after_teacher_approval,
)
from packages.agents.teaching_pack.artifact_fanout import route_after_artifact_workflow
from packages.agents.teaching_pack.quality_routing import route_after_render_quality
from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.teaching_pack.ports import QualityGate

InterruptSpec = list[str] | Literal["*"] | None


class LangGraphRunnableConfig(TypedDict):
    configurable: dict[str, str]
    max_concurrency: NotRequired[int]


def build_teaching_pack_graph(
    *,
    checkpointer=None,
    store=None,
    quality_gate: QualityGate | None = None,
    interrupt_before: InterruptSpec = None,
    interrupt_after: InterruptSpec = None,
):
    """Build the Teaching Pack stage graph without initializing external clients.

    Args:
        checkpointer: LangGraph checkpointer for thread state (per-run).
        store: LangGraph BaseStore for cross-run memory (agent-interaction/002a).
            Pass a PostgresStore (production) or InMemoryStore (development).
            Nodes that need cross-run memory declare `store: BaseStore` in signature.
        quality_gate: Optional quality gate injected into the render_quality node.
    """
    from langgraph.graph import END, StateGraph
    from packages.agents.teaching_pack.artifact_fanout import GENERATE_ONE_ARTIFACT_NODE
    from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact

    graph = StateGraph(TeachingPackState)
    for stage in TEACHING_PACK_STAGES:
        graph.add_node(stage.value, make_stage_node(stage, quality_gate=quality_gate, store=store))
    graph.add_node(GENERATE_ONE_ARTIFACT_NODE, generate_one_artifact)

    first_stage = TEACHING_PACK_STAGES[0]
    graph.set_entry_point(first_stage.value)

    previous = first_stage
    for stage in TEACHING_PACK_STAGES[1:]:
        if previous is TeachingPackStage.TRIAGE:
            graph.add_conditional_edges(
                previous.value,
                route_after_triage,
                {
                    TeachingPackStage.UNIT_PLANNING.value: TeachingPackStage.UNIT_PLANNING.value,
                    TeachingPackStage.PREPLANNING_SEARCH.value: TeachingPackStage.PREPLANNING_SEARCH.value,
                },
            )
            graph.add_node(
                TeachingPackStage.UNIT_PLANNING.value,
                make_stage_node(TeachingPackStage.UNIT_PLANNING, quality_gate=quality_gate, store=store),
            )
            graph.add_node(
                TeachingPackStage.UNIT_APPROVAL.value,
                make_stage_node(TeachingPackStage.UNIT_APPROVAL, quality_gate=quality_gate, store=store),
            )
            graph.add_node(
                TeachingPackStage.UNIT_PREP.value,
                make_stage_node(TeachingPackStage.UNIT_PREP, quality_gate=quality_gate, store=store),
            )
            graph.add_edge(TeachingPackStage.UNIT_PLANNING.value, TeachingPackStage.UNIT_APPROVAL.value)
            graph.add_conditional_edges(
                TeachingPackStage.UNIT_APPROVAL.value,
                route_after_unit_approval,
                {
                    TeachingPackStage.UNIT_PREP.value: TeachingPackStage.UNIT_PREP.value,
                    TeachingPackStage.UNIT_PLANNING.value: TeachingPackStage.UNIT_PLANNING.value,
                },
            )
            graph.add_edge(TeachingPackStage.UNIT_PREP.value, END)
        elif previous is TeachingPackStage.TEACHER_APPROVAL:
            graph.add_conditional_edges(
                previous.value,
                route_after_teacher_approval,
                {
                    TeachingPackStage.ARTIFACT_WORKFLOW.value: TeachingPackStage.ARTIFACT_WORKFLOW.value,
                    TeachingPackStage.EXPORT_FINALIZE.value: TeachingPackStage.EXPORT_FINALIZE.value,
                },
            )
        elif previous is TeachingPackStage.ARTIFACT_WORKFLOW:
            graph.add_conditional_edges(previous.value, route_after_artifact_workflow)
            graph.add_edge(GENERATE_ONE_ARTIFACT_NODE, TeachingPackStage.ARTIFACT_WORKFLOW.value)
        elif previous is TeachingPackStage.RENDER_QUALITY:
            graph.add_conditional_edges(
                previous.value,
                route_after_render_quality,
                {
                    TeachingPackStage.PLANNING_BLUEPRINT.value: TeachingPackStage.PLANNING_BLUEPRINT.value,
                    TeachingPackStage.POST_BLUEPRINT_RESEARCH.value: TeachingPackStage.POST_BLUEPRINT_RESEARCH.value,
                    TeachingPackStage.ARTIFACT_WORKFLOW.value: TeachingPackStage.ARTIFACT_WORKFLOW.value,
                    TeachingPackStage.COMPLIANCE_GATE.value: TeachingPackStage.COMPLIANCE_GATE.value,
                },
            )
        elif previous is TeachingPackStage.COMPLIANCE_GATE:
            graph.add_conditional_edges(
                previous.value,
                route_after_compliance_gate,
                {
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
        store=store,
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
    from packages.agents.teaching_pack.config import TeachingPackConfig

    config: LangGraphRunnableConfig = {"configurable": {"thread_id": run_id}}
    config["max_concurrency"] = TeachingPackConfig().default_artifact_parallelism
    return config
