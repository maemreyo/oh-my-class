"""Langfuse v4 tracing context managers for pipeline nodes and LLM calls.

Uses SDK v4 OpenTelemetry-based API.
Degrades to no-ops when Langfuse is not configured.
"""

from __future__ import annotations

import logging
from typing import Any

from packages.agents.observability.langfuse_client import (
    get_langfuse_client,
    get_trace_metadata,
)

_LOGGER = logging.getLogger("packages.agents.observability.tracing")


class NoOpTrace:
    def update(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> NoOpTrace:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class LangfuseTrace:
    def __init__(self, observation: Any, client: Any) -> None:
        self.observation = observation
        self.client = client

    def update(self, **kwargs: Any) -> None:
        try:
            self.observation.update(**kwargs)
        except Exception as exc:
            _LOGGER.debug("Langfuse observation update failed: %s", exc)

    def end(self) -> None:
        try:
            self.observation.end()
            self.client.flush()
        except Exception as exc:
            _LOGGER.debug("Langfuse flush failed: %s", exc)

    def __enter__(self) -> LangfuseTrace:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.update(level="ERROR", status_message=str(exc_val)[:500])
        self.end()


def trace_node(agent_name: str, run_id: str, step: int, **kwargs: Any):
    client = get_langfuse_client()

    if client is None:
        return NoOpTrace()

    try:
        metadata = get_trace_metadata(run_id, agent_name, step, **kwargs)
        obs = client.start_observation(
            as_type="span",
            name=agent_name or "node",
            metadata=metadata,
        )
        return LangfuseTrace(obs, client)

    except Exception as exc:
        _LOGGER.debug("Langfuse trace_node failed: %s", exc)
        return NoOpTrace()


def trace_llm_call(agent_name: str, run_id: str, model: str, step: int):
    client = get_langfuse_client()

    if client is None:
        return NoOpTrace()

    try:
        metadata = get_trace_metadata(run_id, agent_name, step)
        metadata["model"] = model
        obs = client.start_observation(
            as_type="generation",
            name=f"llm-call-{agent_name}",
            model=model,
            metadata=metadata,
        )
        return LangfuseTrace(obs, client)

    except Exception as exc:
        _LOGGER.debug("Langfuse trace_llm_call failed: %s", exc)
        return NoOpTrace()
