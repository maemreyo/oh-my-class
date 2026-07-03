from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache
def get_langfuse_config() -> dict[str, str | bool]:
    """Get Langfuse configuration from environment.

    Env var priority: LANGFUSE_BASE_URL > LANGFUSE_HOST > default.
    """
    host = (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("LANGFUSE_HOST")
        or "http://localhost:3001"
    )
    return {
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
        "host": host,
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
