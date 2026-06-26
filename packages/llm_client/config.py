from __future__ import annotations

from packages.agents.config.models import LLM


class LLMClientConfig:
    """Thin wrapper around centralized LLM config for packages/llm_client."""

    def __init__(self) -> None:
        self.base_url = LLM.base_url
        self.api_key = LLM.api_key
        self.timeout_s = LLM.timeout
        self.max_retries = LLM.max_retries
        self.temperature = 0.1
