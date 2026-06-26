"""Tests for the shared event bus (packages.agents.events)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure packages.agents is importable
_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

from packages.agents.events import (
    clear_run,
    emit_run_event,
    get_run_events,
    has_terminal_event,
    subscribe,
    unsubscribe,
)


@pytest.fixture(autouse=True)
def _cleanup_run():
    """Clean up test events after each test."""
    yield
    for run_id in ("test-run-1", "test-run-2"):
        clear_run(run_id)


def test_emit_run_event_stores_event_with_correct_schema():
    emit_run_event("test-run-1", "step_started", {"node": "step_01_preflight"})

    events = get_run_events("test-run-1")
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "step_started"
    assert event["run_id"] == "test-run-1"
    assert "timestamp" in event
    assert event["node"] == "step_01_preflight"


def test_get_run_events_returns_empty_for_unknown_run():
    events = get_run_events("nonexistent-run")
    assert events == []


def test_emit_multiple_events():
    emit_run_event("test-run-1", "step_started", {"node": "a"})
    emit_run_event("test-run-1", "step_completed", {"node": "a"})
    emit_run_event("test-run-2", "step_started", {"node": "b"})

    assert len(get_run_events("test-run-1")) == 2
    assert len(get_run_events("test-run-2")) == 1


def test_has_terminal_event_detects_step_completed():
    assert not has_terminal_event("test-run-1")
    emit_run_event("test-run-1", "step_started", {})
    assert not has_terminal_event("test-run-1")
    emit_run_event("test-run-1", "step_completed", {})
    assert has_terminal_event("test-run-1")


def test_has_terminal_event_detects_run_failed():
    emit_run_event("test-run-1", "run_failed", {"error": "boom"})
    assert has_terminal_event("test-run-1")


def test_has_terminal_event_detects_interrupt():
    emit_run_event("test-run-1", "interrupt", {"gate": "blueprint"})
    assert has_terminal_event("test-run-1")


def test_has_terminal_event_detects_step_failed():
    emit_run_event("test-run-1", "step_failed", {"error": "crash"})
    assert has_terminal_event("test-run-1")


def test_has_terminal_event_ignores_non_terminal():
    emit_run_event("test-run-1", "llm_call_started", {})
    emit_run_event("test-run-1", "llm_call_completed", {})
    assert not has_terminal_event("test-run-1")


def test_event_schema_has_required_fields():
    emit_run_event("test-run-1", "llm_call_started", {"agent": "planner"})
    event = get_run_events("test-run-1")[0]
    assert "event_type" in event
    assert "run_id" in event
    assert "timestamp" in event


def test_no_full_content_in_events():
    long_content = "x" * 1000
    emit_run_event("test-run-1", "llm_call_started", {
        "content": long_content,
        "messages": [{"role": "user", "content": long_content}],
    })
    event = get_run_events("test-run-1")[0]
    assert len(str(event)) < 5000


def test_subscribe_returns_queue():
    queue = subscribe("test-run-1")
    assert isinstance(queue, asyncio.Queue)


def test_subscribe_receives_events():
    queue = subscribe("test-run-1")
    emit_run_event("test-run-1", "step_started", {"node": "x"})
    event = queue.get_nowait()
    assert event["event_type"] == "step_started"


def test_unsubscribe_stops_delivery():
    queue = subscribe("test-run-1")
    unsubscribe("test-run-1", queue)
    emit_run_event("test-run-1", "step_started", {"node": "x"})
    assert queue.empty()


def test_clear_run_removes_events_and_subscribers():
    emit_run_event("test-run-1", "step_started", {})
    queue = subscribe("test-run-1")
    clear_run("test-run-1")
    assert get_run_events("test-run-1") == []
    assert not has_terminal_event("test-run-1")
