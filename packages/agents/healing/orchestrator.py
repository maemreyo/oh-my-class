"""H3 pattern: Central healing orchestrator — one place for all recovery logic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.events import emit_run_event
from packages.agents.healing.circuit_breaker import BreakerStore, CircuitBreaker
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

    def __init__(self, max_retries: int = 3, breaker_store: BreakerStore | None = None):
        self.max_retries = max_retries
        self._breaker_store = breaker_store

    def heal(self, state: TeachingPackState) -> dict[str, Any]:
        state_data: dict[str, Any] = dict(state)
        fail_count = state.get("fail_count", 0) + 1
        fail_type = state.get("fail_type", "validation")
        breaker = _run_breaker(state_data, self.max_retries + 1, self._breaker_store)
        if breaker is not None:
            breaker.record_failure()
            if breaker.exhausted:
                result = escalate.apply(state_data, fail_count)
                _emit_healing_events(state_data, result)
                return result

        if fail_count > self.max_retries:
            result = escalate.apply(state_data, fail_count)
            _emit_healing_events(state_data, result)
            return result

        if fail_count == 1 and fail_type == "transient":
            result = retry.apply(state_data, fail_count)
            _emit_healing_events(state_data, result)
            return result

        if fail_count == 1 and fail_type in ("validation", "score", "content"):
            result = rewrite.apply(state_data, fail_count)
            _emit_healing_events(state_data, result)
            return result

        if fail_count == 2:
            result = reroute.apply(state_data, fail_count)
            _emit_healing_events(state_data, result)
            return result

        if fail_count == 3:
            result = replan.apply(state_data, fail_count)
            _emit_healing_events(state_data, result)
            return result

        result = escalate.apply(state_data, fail_count)
        _emit_healing_events(state_data, result)
        return result


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


def _run_breaker(
    state: dict[str, Any],
    threshold: int,
    store: BreakerStore | None,
) -> CircuitBreaker | None:
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return None
    return CircuitBreaker.run(run_id, threshold=threshold, store=store)


def _emit_healing_events(state: dict[str, Any], result: dict[str, Any]) -> None:
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return
    emit_run_event(run_id, "healing_decision", {
        "fail_count": int(result.get("fail_count", 0)),
        "fail_type": str(state.get("fail_type", "unknown")),
        "fail_layer": str(state.get("fail_layer", "unknown")),
        "healing_strategy": str(result.get("healing_strategy", "unknown")),
        "quality_recovery_route": str(result.get("quality_recovery_route", "")),
    })
    if result.get("escalate") is True:
        emit_run_event(run_id, "escalate", {
            "reason": str(result.get("escalate_reason") or result.get("error") or "Manual review required."),
            "healing_strategy": str(result.get("healing_strategy", "escalate")),
            "fail_count": int(result.get("fail_count", 0)),
        })
