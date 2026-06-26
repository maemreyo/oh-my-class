"""Langfuse observability for the oh-my-class agent pipeline.

Provides tracing helpers that create Langfuse traces/spans/generations
for each pipeline step and LLM call. Degrades gracefully to no-ops
when Langfuse is not configured (missing env vars or package).

Usage in pipeline nodes::

    from packages.agents.observability import trace_node

    def my_node(state):
        with trace_node("my_agent", state["run_id"], step=3) as trace:
            # ... node logic ...
            trace.update(output=result)
            return {"result": result}

Usage in LLM calls::

    from packages.agents.observability import trace_llm_call

    async def call_llm(...):
        with trace_llm_call("planner", run_id, model, step) as trace:
            response = await client.chat.completions.create(...)
            trace.update(
                usage={"prompt_tokens": ..., "completion_tokens": ...},
                output=content,
            )
            return content
"""

from packages.agents.observability.tracing import (
    NoOpTrace,
    trace_llm_call,
    trace_node,
)

__all__ = ["trace_node", "trace_llm_call", "NoOpTrace"]
