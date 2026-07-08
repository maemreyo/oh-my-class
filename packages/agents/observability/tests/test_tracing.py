"""Tests for the Langfuse tracing wrappers — the previously zero-coverage
gap #10 of the real-LLM-integration design interview, 2026-07-08.

No real Langfuse server is required: these tests verify (1) the documented
graceful-degradation fallback (no config → no-op, never raises) actually
works, and (2) when a client IS present, the correct trace metadata/shape is
constructed — using a fake client double, not a live server. A live-server
integration test is deferred until a Langfuse instance is available in this
dev environment (see the design interview for that decision).
"""
from __future__ import annotations

from typing import Any

import pytest

from packages.agents.observability.tracing import NoOpTrace, trace_llm_call, trace_node


def test_trace_node_is_noop_when_langfuse_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("packages.agents.observability.tracing.get_langfuse_client", lambda: None)

    with trace_node("planner", "run-1", 1) as trace:
        trace.update(input="x")  # must not raise even though it's a no-op

    assert isinstance(trace, NoOpTrace)


def test_trace_llm_call_is_noop_when_langfuse_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("packages.agents.observability.tracing.get_langfuse_client", lambda: None)

    with trace_llm_call("content_creator", "run-1", "4omc", 3) as trace:
        trace.update(output={"content_length": 10})

    assert isinstance(trace, NoOpTrace)


class _FakeObservation:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.ended = False

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)

    def end(self) -> None:
        self.ended = True


class _FakeLangfuseClient:
    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []
        self.flushed = False

    def start_observation(self, **kwargs: Any) -> _FakeObservation:
        self.observations.append(kwargs)
        return _FakeObservation()

    def flush(self) -> None:
        self.flushed = True


def test_trace_llm_call_builds_generation_observation_with_correct_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeLangfuseClient()
    monkeypatch.setattr(
        "packages.agents.observability.tracing.get_langfuse_client", lambda: fake_client
    )

    with trace_llm_call("content_creator", "run-42", "4omc", 5) as trace:
        pass  # __exit__ calls end(), which flushes

    assert len(fake_client.observations) == 1
    call = fake_client.observations[0]
    assert call["as_type"] == "generation"
    assert call["model"] == "4omc"
    assert call["name"] == "llm-call-content_creator"
    assert call["metadata"]["model"] == "4omc"
    assert fake_client.flushed is True


class _RaisingObservation:
    def update(self, **kwargs: Any) -> None:
        raise RuntimeError("Langfuse API down")

    def end(self) -> None:
        raise RuntimeError("Langfuse API down")


class _RaisingLangfuseClient:
    def start_observation(self, **kwargs: Any) -> _RaisingObservation:
        return _RaisingObservation()

    def flush(self) -> None:
        raise RuntimeError("Langfuse API down")


def test_trace_llm_call_never_raises_when_langfuse_backend_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of the fallback design: a Langfuse outage must never
    break the teaching-pack pipeline. Simulates a client that constructs
    fine but fails on every subsequent call."""
    monkeypatch.setattr(
        "packages.agents.observability.tracing.get_langfuse_client", lambda: _RaisingLangfuseClient()
    )

    with trace_llm_call("content_creator", "run-1", "4omc", 1) as trace:
        trace.update(output={"content_length": 1})  # swallowed, not raised
    # __exit__ -> end() -> flush(), all of which raise internally — must not propagate here.
