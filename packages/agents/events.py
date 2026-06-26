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
from typing import Any

# In-memory event store — one list per run_id
_event_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
_event_subscribers: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = defaultdict(list)

_TERMINAL_EVENTS = {"step_completed", "run_failed", "interrupt", "step_failed"}


def emit_run_event(run_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Append an event to the run's event log and notify SSE subscribers."""
    event: dict[str, Any] = {
        "event_type": event_type,
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        **data,
    }
    _event_store[run_id].append(event)
    for queue in _event_subscribers[run_id]:
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(event)


def get_run_events(run_id: str) -> list[dict[str, Any]]:
    """Get all events for a run."""
    return list(_event_store.get(run_id, []))


def has_terminal_event(run_id: str) -> bool:
    """Check whether a run has received a terminal event."""
    return any(e["event_type"] in _TERMINAL_EVENTS for e in _event_store.get(run_id, []))


def subscribe(run_id: str) -> asyncio.Queue[dict[str, Any] | None]:
    """Subscribe to live events for a run. Returns a queue."""
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    _event_subscribers[run_id].append(queue)
    return queue


def unsubscribe(run_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
    """Remove a subscriber queue."""
    with contextlib.suppress(ValueError):
        _event_subscribers[run_id].remove(queue)


def clear_run(run_id: str) -> None:
    """Clear events for a run (for testing)."""
    _event_store.pop(run_id, None)
    _event_subscribers.pop(run_id, None)
