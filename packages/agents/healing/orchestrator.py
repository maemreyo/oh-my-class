"""H3 pattern: Central healing orchestrator — one place for all recovery logic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.healing.strategies import escalate, replan, reroute, retry, rewrite

if TYPE_CHECKING:
    from packages.agents.teaching_pack.nodes import TeachingPackState


class HealingOrchestrator:
    """Selects and applies the right healing strategy based on fail signal.

    Strategy selection table:
        fail_count=1, transient   → retry
        fail_count=1, validation/score → rewrite
        fail_count=2              → reroute
        fail_count=3              → replan
        fail_count>3              → escalate
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def heal(self, state: TeachingPackState) -> dict[str, Any]:
        state_data: dict[str, Any] = dict(state)
        fail_count = state.get("fail_count", 0) + 1
        fail_type = state.get("fail_type", "validation")

        if fail_count > self.max_retries:
            return escalate.apply(state_data, fail_count)

        if fail_count == 1 and fail_type == "transient":
            return retry.apply(state_data, fail_count)

        if fail_count == 1 and fail_type in ("validation", "score", "content"):
            return rewrite.apply(state_data, fail_count)

        if fail_count == 2:
            return reroute.apply(state_data, fail_count)

        if fail_count == 3:
            return replan.apply(state_data, fail_count)

        return escalate.apply(state_data, fail_count)


def healing_node(state: TeachingPackState) -> dict[str, Any]:
    """Graph node — delegates to HealingOrchestrator."""
    from packages.agents.config.gate_config import GateConfig
    config = GateConfig()
    return HealingOrchestrator(max_retries=config.max_retries).heal(state)


def route_after_healing(state: TeachingPackState) -> str:
    if state.get("escalate"):
        return "escalate_node"
    artifacts = state.get("artifacts") or []
    if any(a.get("metadata", {}).get("placeholder") for a in artifacts):
        return "escalate_node"
    return "step_08_generate"
