"""Shared event bus for pipeline observability.

Both the LLM layer (packages/agents/llm/) and the gateway SSE stream
(services/gateway/routers/runs.py) read/write to this store.

INVARIANT-02 safe: lives in packages/agents/, not services/.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

type ObservabilityEventType = Literal[
    "stage_transition",
    "gate_decision",
    "healing_decision",
    "hard_block_violation",
    "escalate",
    "cost_accrued",
    "run_failed",
    "interrupt",
    "step",
    "llm_call_started",
    "llm_call_completed",
    "llm_call_failed",
    "breaker_tripped",
    "component_strategy",
    # SDE-11: lightweight editor success observability (ADR-047 decision 15).
    # No dashboard reads these -- they're persisted the same way as any other
    # observability event (`TeachingPackRunStore.write_observability_event`,
    # called directly from the gateway's slide-deck-editor request handlers,
    # not via the in-memory `publish_event`/drain path those handlers never
    # run through) for a manual query 4-6 weeks post-launch.
    "slide_deck_edited_within_24h",
    "slide_deck_ai_rewrite_suggested",
    "slide_deck_ai_rewrite_accepted",
    "slide_deck_ai_rewrite_cancelled",
    "slide_deck_editor_return_usage",
    # #463 rollout: fires whenever `ArtifactDocumentStore.get_preview_source`
    # falls back to a legacy V1 `ArtifactSnapshot` (no linked V2 document yet)
    # -- the explicit metric the V1-writer deprecation/deletion date depends on.
    "artifact_document_legacy_read",
]


class ObservabilityEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4()}", min_length=1)
    run_id: str = Field(min_length=1, max_length=64)
    event_type: ObservabilityEventType
    payload: JsonObject = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    teacher_id: str | None = Field(default=None, max_length=64)
    stage: str | None = Field(default=None, max_length=64)
    sequence: int | None = Field(default=None, ge=1)

    def legacy_dict(self) -> JsonObject:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            **self.payload,
        }

# In-memory event store — one list per run_id
_event_store: dict[str, list[JsonObject]] = defaultdict(list)
_event_subscribers: dict[str, list[asyncio.Queue[JsonObject | None]]] = defaultdict(list)

_TERMINAL_EVENTS = {"run_failed", "interrupt"}
_OBSERVABILITY_FIELDS = {"event_id", "event_type", "run_id", "timestamp", "teacher_id", "sequence"}


def emit_run_event(run_id: str, event_type: ObservabilityEventType, data: JsonObject) -> None:
    """Append an event to the run's event log and notify SSE subscribers."""
    publish_event(ObservabilityEvent(run_id=run_id, event_type=event_type, payload=data))


def publish_event(event: ObservabilityEvent) -> None:
    legacy_event = event.legacy_dict()
    _event_store[event.run_id].append(legacy_event)
    for queue in _event_subscribers[event.run_id]:
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(legacy_event)


def get_run_events(run_id: str) -> list[JsonObject]:
    """Get all events for a run."""
    return list(_event_store.get(run_id, []))


def get_observability_events(run_id: str) -> list[ObservabilityEvent]:
    return [
        _observability_event_from_legacy(event)
        for event in _event_store.get(run_id, [])
    ]


def drain_observability_events(run_id: str) -> list[ObservabilityEvent]:
    events = get_observability_events(run_id)
    _event_store.pop(run_id, None)
    return events


def has_terminal_event(run_id: str) -> bool:
    """Check whether a run has received a terminal event."""
    return any(e["event_type"] in _TERMINAL_EVENTS for e in _event_store.get(run_id, []))


def subscribe(run_id: str) -> asyncio.Queue[JsonObject | None]:
    """Subscribe to live events for a run. Returns a queue."""
    queue: asyncio.Queue[JsonObject | None] = asyncio.Queue()
    _event_subscribers[run_id].append(queue)
    return queue


def unsubscribe(run_id: str, queue: asyncio.Queue[JsonObject | None]) -> None:
    """Remove a subscriber queue."""
    with contextlib.suppress(ValueError):
        _event_subscribers[run_id].remove(queue)


def clear_run(run_id: str) -> None:
    """Clear events for a run (for testing)."""
    _event_store.pop(run_id, None)
    _event_subscribers.pop(run_id, None)


def _observability_event_from_legacy(event: JsonObject) -> ObservabilityEvent:
    payload = {
        key: value
        for key, value in event.items()
        if key not in _OBSERVABILITY_FIELDS
    }
    return ObservabilityEvent.model_validate({**event, "payload": payload})
