"""Langfuse configuration for oh-my-class.

Integration points:
1. LangGraph nodes — trace each pipeline step
2. LiteLLM proxy — cost tracking per agent per run
3. Agent calls — trace individual LLM calls with metadata

All traces include:
- run_id: links to OhMyClassState.run_id
- agent: which agent made the call
- step: which pipeline step (1-13)
- cost: token usage and cost attribution
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache
def get_langfuse_config() -> dict[str, str | bool]:
    """Get Langfuse configuration from environment."""
    return {
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
        "host": os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
        "enabled": bool(os.environ.get("LANGFUSE_PUBLIC_KEY")),
    }


def get_trace_metadata(
    run_id: str,
    agent: str,
    step: int,
    teacher_id: str | None = None,
) -> dict[str, Any]:
    """Get standard metadata for Langfuse traces."""
    return {
        "run_id": run_id,
        "agent": agent,
        "step": step,
        "teacher_id": teacher_id or "unknown",
        "pipeline": "oh-my-class",
    }
