"""Langfuse tracing helpers for LangGraph nodes.

Usage in pipeline nodes:

    from observability.tracing import trace_node, trace_llm_call

    def design_lesson_plan(state: OhMyClassState) -> dict:
        with trace_node("planner", state["run_id"], step=3) as trace:
            # ... node logic ...
            trace.update(output=lesson_plan)
            return {"lesson_plan": lesson_plan}
"""

from contextlib import contextmanager

from .langfuse_config import get_langfuse_config, get_trace_metadata


@contextmanager
def trace_node(agent_name: str, run_id: str, step: int, **kwargs):
    """Trace a LangGraph node execution.

    Creates a span in Langfuse for the node, with automatic timing.
    """
    config = get_langfuse_config()

    if not config["enabled"]:
        # No-op when Langfuse not configured
        yield _NoOpTrace()
        return

    try:
        from langfuse import Langfuse
        langfuse = Langfuse(
            public_key=config["public_key"],
            secret_key=config["secret_key"],
            host=config["host"],
        )

        metadata = get_trace_metadata(run_id, agent_name, step, **kwargs)

        # Create a trace for the run (if not exists)
        trace = langfuse.trace(
            name=f"pipeline-step-{step}",
            metadata=metadata,
            session_id=run_id,
        )

        # Create a span for this specific node
        span = trace.span(
            name=agent_name,
            metadata=metadata,
        )

        yield _LangfuseTrace(trace, span, langfuse)

    except ImportError:
        # langfuse not installed — degrade gracefully
        yield _NoOpTrace()
    except Exception as e:
        # Don't let tracing failures break the pipeline
        print(f"⚠️  Langfuse tracing error: {e}")
        yield _NoOpTrace()


@contextmanager
def trace_llm_call(agent_name: str, run_id: str, model: str, step: int):
    """Trace an individual LLM call with model and token info."""
    config = get_langfuse_config()

    if not config["enabled"]:
        yield _NoOpTrace()
        return

    try:
        from langfuse import Langfuse
        langfuse = Langfuse(
            public_key=config["public_key"],
            secret_key=config["secret_key"],
            host=config["host"],
        )

        metadata = get_trace_metadata(run_id, agent_name, step)
        metadata["model"] = model

        trace = langfuse.trace(
            name=f"llm-call-{agent_name}",
            metadata=metadata,
            session_id=run_id,
        )

        generation = trace.generation(
            name=agent_name,
            model=model,
            metadata=metadata,
        )

        yield _LangfuseTrace(trace, generation, langfuse)

    except ImportError:
        yield _NoOpTrace()
    except Exception as e:
        print(f"⚠️  Langfuse tracing error: {e}")
        yield _NoOpTrace()


class _NoOpTrace:
    """No-op trace when Langfuse is not configured."""

    def update(self, **kwargs):
        pass

    def end(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _LangfuseTrace:
    """Wrapper around Langfuse trace/span for cleanup."""

    def __init__(self, trace, span, langfuse_client):
        self.trace = trace
        self.span = span
        self.client = langfuse_client

    def update(self, **kwargs):
        """Update the span with output data."""
        if hasattr(self.span, "update"):
            self.span.update(**kwargs)

    def end(self):
        """End the span and flush to Langfuse."""
        if hasattr(self.span, "end"):
            self.span.end()
        self.client.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.span.update(level="ERROR", status_message=str(exc_val))
        self.end()
