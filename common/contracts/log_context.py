"""Log context Pydantic model — structured metadata for observability.

Provides a typed context object attached to every log entry and LLM call,
enabling per-request, per-run, and per-agent cost attribution and tracing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LogContext(BaseModel):
    """Structured log context for pipeline observability.

    Attached to every log entry and LLM call. The ``bind()`` class method
    produces a new instance with selected fields updated, keeping the original
    immutable.
    """

    request_id: str = Field(
        default="", description="Unique request identifier (UUIDv4)"
    )
    teacher_id: str = Field(default="", description="Authenticated teacher ID")
    run_id: str = Field(default="", description="Pipeline run identifier")
    step: int | None = Field(
        default=None, description="Current pipeline step (1-13)"
    )
    agent: str | None = Field(default=None, description="Current agent name")
    timestamp: str = Field(default="", description="ISO 8601 timestamp")

    def bind(self, **kwargs: object) -> LogContext:
        """Return a new LogContext with *kwargs* overriding current values.

        The original instance is never mutated.
        """
        return self.model_copy(update=kwargs)
