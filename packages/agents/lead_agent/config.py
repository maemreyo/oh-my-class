"""Lead Agent configuration — model, tools, and runtime parameters.

Configuration is driven by this file and by agents-config.yaml.
Do not hardcode model names or tool lists in agent logic.
"""

from __future__ import annotations

from typing import Any, TypedDict


class LeadAgentConfig(TypedDict):
    """Configuration for the Lead Agent."""

    model: str
    fallback: str
    tools: list[str]
    max_turns: int
    temperature: float
    metadata_tags: list[str]


# The Lead Agent uses gpt-5.4 via 9Router combo: 4omc
# (NOT direct OpenAI API — all traffic routes through 9Router sidecar)
LEAD_AGENT_CONFIG: LeadAgentConfig = {
        "model": "gpt-5.4",        # → 9Router combo: 4omc (best free model)
    "fallback": "deepseek-v4-flash",  # → 9Router combo: f.light (fast fallback)
    "tools": ["task", "ask_clarification", "read_file", "write_file"],
    "max_turns": 0,  # Unlimited (pipeline steps)
    "temperature": 0.3,
    "metadata_tags": ["agent:lead", "pipeline:oh-my-class"],
}


# Per-call metadata template — every LLM call must include these tags
# for cost attribution (INVARIANT-07).
CALL_METADATA_TEMPLATE: dict[str, Any] = {
    "tags": [
        "agent:lead",
        "pipeline:oh-my-class",
        # "step:{step}" and "run:{run_id}" are filled at call time
    ],
}
