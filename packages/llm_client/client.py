"""LLMClient: thin wrapper over openai.AsyncOpenAI.

All agents receive an LLMClient instance via dependency injection.
Never instantiate openai.AsyncOpenAI directly inside agent code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

import openai

from packages.llm_client.budget.manager import TokenBudgetManager
from packages.llm_client.config import LLMClientConfig
from packages.llm_client.tags import build_tags

_budget = TokenBudgetManager()  # module-level singleton


@dataclass
class ChatMessage:
    role: str       # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cached: bool = False


class LLMClient:
    """Wrapper over openai.AsyncOpenAI pointed at configured endpoint.

    Local:      base_url = http://localhost:20128 (9Router)
    Production: base_url = http://litellm:4000   (LiteLLM)

    Both expose OpenAI-compatible API — client code is identical.
    No fallback/retry logic here — that boundary belongs to LiteLLM (infra)
    and healing_node (content quality).
    """

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        self._config = config or LLMClientConfig()
        self._client = openai.AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout_s,
            max_retries=self._config.max_retries,
        )

    async def chat(
        self,
        model: str,                         # "f.light" | "f.pro" — always
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        step: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> ChatResponse:
        """Send chat request. Returns ChatResponse with usage stats."""
        extra = build_tags(agent, task, run_id, step)

        # Budget: use configured hard limit for bounded tasks; None lets model generate freely
        budget_hard_limit = _budget.get_hard_limit(task)
        effective_max_tokens = max_tokens if max_tokens is not None else budget_hard_limit

        kwargs: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self._config.temperature,
            "extra_body": extra,
        }
        if effective_max_tokens is not None:
            kwargs["max_tokens"] = effective_max_tokens
        if response_format is not None:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        cached = getattr(usage, "cached_tokens", 0) > 0 if usage else False

        # Record usage for EMA adaptation and soft-limit warnings
        _budget.record_usage(task, output_tokens)

        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached=cached,
        )

    async def stream(
        self,
        model: str,
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        step: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat response token by token."""
        extra = build_tags(agent, task, run_id, step)
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=self._config.temperature,
            extra_body=extra,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
