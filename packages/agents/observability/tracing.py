"""Langfuse tracing context managers for pipeline nodes and LLM calls.

Provides `trace_node()` for LangGraph node execution tracing
and `trace_llm_call()` for individual LLM call tracing.

Both degrade to no-ops when Langfuse is not configured.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from packages.agents.observability.langfuse_client import (
    get_langfuse_client,
    get_trace_metadata,
)

_LOGGER = logging.getLogger("packages.agents.observability.tracing")


class NoOpTrace:
    """No-op trace when Langfuse is not configured or fails."""

    def update(self, **kwargs: Any) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> NoOpTrace:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class LangfuseTrace:
    """Wrapper around Langfuse trace/span for cleanup and updates."""

    def __init__(self, trace: Any, span: Any, client: Any) -> None:
        self.trace = trace
        self.span = span
        self.client = client

    def update(self, **kwargs: Any) -> None:
        """Update the span with output data."""
        if hasattr(self.span, "update"):
            try:
                self.span.update(**kwargs)
            except Exception as exc:
                _LOGGER.debug("Langfuse span update failed: %s", exc)

    def end(self) -> None:
        """End the span and flush to Langfuse."""
        try:
            if hasattr(self.span, "end"):
                self.span.end()
            self.client.flush()
        except Exception as exc:
            _LOGGER.debug("Langfuse span end failed: %s", exc)

    def __enter__(self) -> LangfuseTrace:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.update(level="ERROR", status_message=str(exc_val))
        self.end()


class LangfuseGeneration:
    """Wrapper around Langfuse generation (LLM call) for cleanup and updates."""

    def __init__(self, trace: Any, generation: Any, client: Any) -> None:
        self.trace = trace
        self.generation = generation
        self.client = client

    def update(self, **kwargs: Any) -> None:
        """Update the generation with output/usage data."""
        if hasattr(self.generation, "update"):
            try:
                self.generation.update(**kwargs)
            except Exception as exc:
                _LOGGER.debug("Langfuse generation update failed: %s", exc)

    def end(self) -> None:
        """End the generation and flush to Langfuse."""
        try:
            if hasattr(self.generation, "end"):
                self.generation.end()
            self.client.flush()
        except Exception as exc:
            _LOGGER.debug("Langfuse generation end failed: %s", exc)

    def __enter__(self) -> LangfuseGeneration:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.update(level="ERROR", status_message=str(exc_val))
        self.end()


@contextmanager
def trace_node(agent_name: str, run_id: str, step: int, **kwargs: Any):
    """Trace a LangGraph node execution.

    Creates a span in Langfuse for the node, with automatic timing.

    Usage::

        with trace_node("planner", state["run_id"], step=3) as trace:
            # ... node logic ...
            trace.update(output=lesson_plan)
    """
    client = get_langfuse_client()

    if client is None:
        yield NoOpTrace()
        return

    try:
        metadata = get_trace_metadata(run_id, agent_name, step, **kwargs)

        trace = client.trace(
            name=f"pipeline-step-{step}",
            metadata=metadata,
            session_id=run_id,
        )

        span = trace.span(
            name=agent_name,
            metadata=metadata,
        )

        yield LangfuseTrace(trace, span, client)

    except Exception as exc:
        _LOGGER.debug("Langfuse trace_node failed: %s", exc)
        yield NoOpTrace()


@contextmanager
def trace_llm_call(agent_name: str, run_id: str, model: str, step: int):
    """Trace an individual LLM call with model and token info.

    Usage::

        with trace_llm_call("planner", run_id, "deepseek-v4-flash", 3) as trace:
            response = await client.chat.completions.create(...)
            trace.update(
                usage={"prompt_tokens": ..., "completion_tokens": ...},
                output=content,
            )
    """
    client = get_langfuse_client()

    if client is None:
        yield NoOpTrace()
        return

    try:
        metadata = get_trace_metadata(run_id, agent_name, step)
        metadata["model"] = model

        trace = client.trace(
            name=f"llm-call-{agent_name}",
            metadata=metadata,
            session_id=run_id,
        )

        generation = trace.generation(
            name=agent_name,
            model=model,
            metadata=metadata,
        )

        yield LangfuseGeneration(trace, generation, client)

    except Exception as exc:
        _LOGGER.debug("Langfuse trace_llm_call failed: %s", exc)
        yield NoOpTrace()
