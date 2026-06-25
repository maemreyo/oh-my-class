"""Cost attribution metadata tags.

All agent calls include these tags — LiteLLM logs them for per-agent cost tracking.
9Router silently ignores the metadata field (OpenAI-compatible extra_body).
"""
from __future__ import annotations

from typing import Any


def build_tags(
    agent: str,
    task: str,
    run_id: str | None = None,
    step: int | None = None,
) -> dict[str, Any]:
    """Build metadata tags dict for LiteLLM cost attribution.

    Args:
        agent:  agent name, e.g. "content_creator", "llm_judge"
        task:   task type, e.g. "content_generation", "fact_verification"
        run_id: graph run ID for per-run cost breakdown
        step:   current pipeline step number (1–13) for per-step cost breakdown

    Returns metadata dict passed as extra_body to LLM calls.
    """
    tags: list[str] = [
        f"agent:{agent}",
        f"task:{task}",
        "pipeline:oh-my-class",
    ]
    if step is not None:
        tags.append(f"step:{step}")
    if run_id:
        tags.append(f"run:{run_id}")

    return {"metadata": {"tags": tags}}
