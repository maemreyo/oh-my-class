"""LLMClient: thin wrapper over openai.AsyncOpenAI.

All agents receive an LLMClient instance via dependency injection.
Never instantiate openai.AsyncOpenAI directly inside agent code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import openai
from openai import Omit

from packages.llm_client.budget.manager import TokenBudgetManager
from packages.llm_client.circuit_breaker import breaker_for
from packages.llm_client.config import LLMClientConfig
from packages.llm_client.errors import classify_openai_error
from packages.llm_client.middleware import (
    CallMiddlewareRunner,
    MiddlewareCallContext,
    MiddlewareMessage,
    expects_json_from_response_format,
)
from packages.llm_client.tags import build_tags

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    # AsyncOpenAI/ChatCompletionSystemMessageParam/ChatCompletionUserMessageParam are
    # unused here but re-exported so callers outside llm_client don't import openai directly.
    from openai import AsyncOpenAI as AsyncOpenAI
    from openai.types.chat import (
        ChatCompletionMessageParam,
        completion_create_params,
    )
    from openai.types.chat import (
        ChatCompletionSystemMessageParam as ChatCompletionSystemMessageParam,
    )
    from openai.types.chat import (
        ChatCompletionUserMessageParam as ChatCompletionUserMessageParam,
    )

_OMIT: Omit = Omit()

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


class ProviderCircuitOpenError(RuntimeError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Provider circuit is open for {provider}")


class LLMClient:
    """Wrapper over openai.AsyncOpenAI pointed at configured endpoint.

    Local:      base_url = http://localhost:20228/v1 (host 9Router)
    Production: base_url = http://litellm:4000   (LiteLLM)

    Both expose OpenAI-compatible API — client code is identical.
    No fallback/retry logic here — that boundary belongs to LiteLLM (infra)
    and healing_node (content quality).
    """

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        self._config = config or LLMClientConfig()
        self._middleware = CallMiddlewareRunner()
        self._client = openai.AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout_s,
            max_retries=self._config.max_retries,
        )

    async def chat(
        self,
        model: str,                         # "f.light" | "4omc" — always
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        step: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        locale: str | None = None,
        response_format: completion_create_params.ResponseFormat | Omit = _OMIT,
    ) -> ChatResponse:
        """Send chat request. Returns ChatResponse with usage stats."""
        breaker = breaker_for(model)
        if breaker.is_open():
            raise ProviderCircuitOpenError(model)

        context = MiddlewareCallContext(
            agent=agent,
            task=task,
            run_id=run_id,
            step=step,
            locale=locale,
            expects_json=expects_json_from_response_format(response_format),
        )
        messages = [
            ChatMessage(role=message.role, content=message.content)
            for message in self._middleware.before_call(
                [MiddlewareMessage(role=message.role, content=message.content) for message in messages],
                context,
            )
        ]
        extra = build_tags(agent, task, run_id, step)

        # Budget: use configured hard limit for bounded tasks; None lets model generate freely
        budget_hard_limit = _budget.get_hard_limit(task)
        effective_max_tokens = max_tokens if max_tokens is not None else budget_hard_limit

        typed_messages = cast(
            "list[ChatCompletionMessageParam]",
            [{"role": m.role, "content": m.content} for m in messages],
        )
        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=temperature if temperature is not None else self._config.temperature,
                extra_body=extra,
                max_tokens=effective_max_tokens,
                response_format=response_format,
            )
        except openai.OpenAIError as exc:
            breaker.record_failure()
            raise classify_openai_error(exc) from exc
        breaker.record_success()
        choice = resp.choices[0]
        usage = resp.usage

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        cached = getattr(usage, "cached_tokens", 0) > 0 if usage else False

        # Record usage for EMA adaptation and soft-limit warnings
        _budget.record_usage(task, output_tokens)

        result = self._middleware.after_call(choice.message.content or "", context)
        return ChatResponse(
            content=result.content,
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
        locale: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat response token by token.

        Deliberately does NOT run after_call (PII scrub/unsafe-output
        block/JSON repair/locale check) — that transform needs the whole
        document, not a partial token, and running it per-chunk would be
        wrong (patterns can span chunk boundaries). Only use this for a
        caller that genuinely displays/consumes tokens incrementally. If a
        caller just accumulates every chunk into one string before doing
        anything with it, use chat_via_streaming_transport() instead — same
        streaming HTTP transport, but with the full chat()-parity safety
        pipeline applied to the accumulated result.
        """
        breaker = breaker_for(model)
        if breaker.is_open():
            raise ProviderCircuitOpenError(model)

        context = MiddlewareCallContext(agent=agent, task=task, run_id=run_id, step=step, locale=locale)
        messages = [
            ChatMessage(role=message.role, content=message.content)
            for message in self._middleware.before_call(
                [MiddlewareMessage(role=message.role, content=message.content) for message in messages],
                context,
            )
        ]
        extra = build_tags(agent, task, run_id, step)
        # Budget parity with chat(): the streaming path must honour the agent's token
        # budget too — otherwise the highest-budget agent (content_creator) silently
        # streamed with no max_tokens (regression caught by test_max_tokens).
        effective_max_tokens = max_tokens if max_tokens is not None else _budget.get_hard_limit(task)
        typed_messages = cast(
            "list[ChatCompletionMessageParam]",
            [{"role": m.role, "content": m.content} for m in messages],
        )
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=self._config.temperature,
                extra_body=extra,
                max_tokens=effective_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.OpenAIError as exc:
            breaker.record_failure()
            raise classify_openai_error(exc) from exc
        breaker.record_success()

    async def chat_via_streaming_transport(
        self,
        model: str,
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        step: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        locale: str | None = None,
    ) -> ChatResponse:
        """Full-response chat that uses the streaming HTTP transport internally.

        For callers who pick a streaming network transport (e.g. to avoid
        provider response-size limits) but only ever consume the fully
        accumulated text — same safety guarantees as chat(): before_call AND
        after_call (PII scrub, unsafe-output block, JSON repair, locale check)
        both run, on the complete content. Use plain stream() only when a
        caller genuinely needs raw token-by-token output; that path does not
        run after_call, since after_call transforms the whole document.
        """
        breaker = breaker_for(model)
        if breaker.is_open():
            raise ProviderCircuitOpenError(model)

        context = MiddlewareCallContext(
            agent=agent, task=task, run_id=run_id, step=step, locale=locale,
        )
        prepared_messages = [
            ChatMessage(role=message.role, content=message.content)
            for message in self._middleware.before_call(
                [MiddlewareMessage(role=message.role, content=message.content) for message in messages],
                context,
            )
        ]
        extra = build_tags(agent, task, run_id, step)
        effective_max_tokens = max_tokens if max_tokens is not None else _budget.get_hard_limit(task)
        typed_messages = cast(
            "list[ChatCompletionMessageParam]",
            [{"role": m.role, "content": m.content} for m in prepared_messages],
        )
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=temperature if temperature is not None else self._config.temperature,
                extra_body=extra,
                max_tokens=effective_max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            chunks: list[str] = []
            response_model = model
            input_tokens = 0
            output_tokens = 0
            async for chunk in stream:
                response_model = getattr(chunk, "model", None) or response_model
                if getattr(chunk, "choices", None):
                    delta = chunk.choices[0].delta.content
                    if delta:
                        chunks.append(delta)
                usage = getattr(chunk, "usage", None)
                if usage:
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens
        except openai.OpenAIError as exc:
            breaker.record_failure()
            raise classify_openai_error(exc) from exc
        breaker.record_success()

        _budget.record_usage(task, output_tokens)
        result = self._middleware.after_call("".join(chunks), context)
        return ChatResponse(
            content=result.content,
            model=response_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
