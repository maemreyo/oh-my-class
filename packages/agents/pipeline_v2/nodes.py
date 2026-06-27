"""Placeholder Pipeline V2 stage nodes.

These nodes intentionally perform no LLM, network, database, or Langfuse work.
They exist only to make the V2 graph topology compile while later issues fill in
stage implementations behind explicit ports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from packages.agents.pipeline_v2.stages import PipelineV2Stage


class PipelineV2State(TypedDict):
    """Minimal V2 state shape used by the foundation graph skeleton."""

    run_id: str
    current_stage: NotRequired[str]
    completed_stages: NotRequired[list[str]]


def make_stage_node(stage: PipelineV2Stage):
    """Create a pure placeholder node for a Pipeline V2 stage."""

    def stage_node(state: PipelineV2State) -> PipelineV2State:
        completed = [*state.get("completed_stages", []), stage.value]
        return {
            "run_id": state["run_id"],
            "current_stage": stage.value,
            "completed_stages": completed,
        }

    stage_node.__name__ = stage.value
    return stage_node
