"""Gate trust-score computation backed by BaseStore.

Trust score = rolling average of the last WINDOW_SIZE gate events:
  approve         → weight 1.0
  edited /
  request_edits   → weight 0.5
  reject          → weight 0.0

Score is per (teacher_id, gate_name). Updated on every gate close regardless
of whether the fast-lane is active — history accumulates even when the feature
is disabled, so trust builds up before the operator opts in.

Fast-lane gates: content_approval, blueprint_approval only.
clarification_required and contract_confirmation are hard-excluded.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.teaching_pack.store_namespaces import (
    TEACHER_PREFS_TTL_MINUTES,
    teacher_preferences_ns,
)

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

_WINDOW_SIZE: int = 10
_EVENT_WEIGHTS: dict[str, float] = {
    "approve": 1.0,
    "auto_approved": 1.0,
    "edit": 0.5,
    "request_edits": 0.5,
    "reject": 0.0,
}

_FAST_LANE_ELIGIBLE_GATES: frozenset[str] = frozenset({
    "content_approval",
    "blueprint_approval",
})
_FAST_LANE_EXCLUDED_GATES: frozenset[str] = frozenset({
    "clarification_required",
    "contract_confirmation",
})


def is_fast_lane_eligible(gate_name: str) -> bool:
    """Return True when gate_name can be auto-approved via the fast-lane.

    clarification_required and contract_confirmation always return False —
    they require teacher input regardless of trust score.
    """
    return gate_name in _FAST_LANE_ELIGIBLE_GATES


def record_gate_event(
    store: BaseStore,
    teacher_id: str,
    gate_name: str,
    action: str,
    artifact_types: list[str],
) -> None:
    """Append a gate-close event to the teacher's rolling history.

    History is capped at WINDOW_SIZE * 2 entries; oldest events are dropped.
    Called on every gate close (auto-approved and human-reviewed alike).
    """
    ns = teacher_preferences_ns(teacher_id)
    key = f"gate_trust::{gate_name}"
    existing = store.get(ns, key)
    events: list[dict[str, object]] = []
    if existing is not None and isinstance(existing.value, dict):
        raw = existing.value.get("events")
        if isinstance(raw, list):
            events = [e for e in raw if isinstance(e, dict)]
    events.append({"action": action, "artifact_types": artifact_types})
    if len(events) > _WINDOW_SIZE * 2:
        events = events[len(events) - _WINDOW_SIZE * 2:]
    store.put(ns, key, {"events": events}, ttl=TEACHER_PREFS_TTL_MINUTES)


def compute_trust_score(
    store: BaseStore,
    teacher_id: str,
    gate_name: str,
) -> float:
    """Return rolling trust score in [0.0, 1.0] for teacher + gate.

    Returns 0.0 when no history exists (no false positives on new teachers).
    Only the most recent WINDOW_SIZE events contribute to the score.
    """
    ns = teacher_preferences_ns(teacher_id)
    key = f"gate_trust::{gate_name}"
    result = store.get(ns, key)
    if result is None or not isinstance(result.value, dict):
        return 0.0
    raw = result.value.get("events")
    if not isinstance(raw, list) or not raw:
        return 0.0
    window = [e for e in raw if isinstance(e, dict)][-_WINDOW_SIZE:]
    total = sum(
        _EVENT_WEIGHTS.get(str(event.get("action", "")), 0.0)
        for event in window
    )
    return total / len(window)


def should_fast_lane(
    store: BaseStore,
    teacher_id: str,
    gate_name: str,
    threshold: float,
) -> bool:
    """Return True when gate should be auto-approved for this teacher.

    Preconditions checked (all must hold):
    - gate is in FAST_LANE_ELIGIBLE_GATES
    - teacher trust score ≥ threshold
    - threshold > 0 (threshold of 0 would fast-lane everyone, disallow)
    """
    if not is_fast_lane_eligible(gate_name):
        return False
    if threshold <= 0.0:
        return False
    return compute_trust_score(store, teacher_id, gate_name) >= threshold
