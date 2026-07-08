from __future__ import annotations

import anyio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from packages.agents.llm import chat_messages, log_llm_failure, log_llm_start, log_llm_success

if TYPE_CHECKING:
    from packages.agents.prompts.compiler import CompiledPrompt
    from packages.llm_client.client import ChatCompletionMessageParam


class AgentCall(Protocol):
    async def __call__(
        self,
        *,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        tags: list[str],
    ) -> str: ...


class RetryMessageBuilder(Protocol):
    def __call__(
        self,
        error: BaseException,
        last_content: str | None,
    ) -> list[ChatCompletionMessageParam]: ...


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    agent: str
    run_id: str
    step: int
    step_label: str
    model: str
    max_retries: int = 3
    base_temperature: float = 0.7
    retry_temperature: float = 0.3
    backoff_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    config: AgentRuntimeConfig

    def messages(self, system: str, user: str) -> list[ChatCompletionMessageParam]:
        return chat_messages(system, user)

    async def complete_json(
        self,
        *,
        messages: list[ChatCompletionMessageParam],
        attempt: int,
        extra_tags: tuple[str, ...] = (),
        temperature: float | None = None,
    ) -> str:
        from packages.agents import llm

        return await self._call_once(
            messages=messages,
            attempt=attempt,
            extra_tags=extra_tags,
            temperature=temperature,
            call=lambda *, messages, temperature, tags: llm.complete_json_chat(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                tags=tags,
            ),
        )

    async def complete_json_with_retries[T](
        self,
        *,
        messages: list[ChatCompletionMessageParam],
        parse: Callable[[str], T],
        retry_messages: RetryMessageBuilder,
        extra_tags: tuple[str, ...] = (),
    ) -> T:
        last_content: str | None = None
        current_messages = messages
        for attempt in range(self.config.max_retries):
            try:
                last_content = await self.complete_json(
                    messages=current_messages,
                    attempt=attempt,
                    extra_tags=extra_tags,
                )
                return parse(last_content)
            except Exception as exc:
                if attempt + 1 >= self.config.max_retries:
                    raise
                current_messages = retry_messages(exc, last_content)
        raise RuntimeError("agent_runtime_retry_exhausted")  # noqa: TRY003

    async def complete_compiled_json(
        self,
        *,
        compiled: CompiledPrompt,
        messages: list[ChatCompletionMessageParam],
        attempt: int,
        extra_tags: tuple[str, ...] = (),
        temperature: float | None = None,
    ) -> str:
        from packages.agents.llm import compiled_chat

        return await self._call_once(
            messages=messages,
            attempt=attempt,
            extra_tags=extra_tags,
            temperature=temperature,
            call=lambda *, messages, temperature, tags: compiled_chat.compiled_json_chat(
                model=self.config.model,
                compiled=compiled,
                messages=messages,
                temperature=temperature,
                tags=tags,
            ),
        )

    async def complete_compiled_json_with_retries[T](
        self,
        *,
        compiled: CompiledPrompt,
        messages: list[ChatCompletionMessageParam],
        parse: Callable[[str], T],
        retry_messages: RetryMessageBuilder,
        extra_tags: tuple[str, ...] = (),
    ) -> T:
        last_content: str | None = None
        current_messages = messages
        for attempt in range(self.config.max_retries):
            try:
                last_content = await self.complete_compiled_json(
                    compiled=compiled,
                    messages=current_messages,
                    attempt=attempt,
                    extra_tags=extra_tags,
                )
                return parse(last_content)
            except Exception as exc:
                if attempt + 1 >= self.config.max_retries:
                    raise
                current_messages = retry_messages(exc, last_content)
        raise RuntimeError("agent_runtime_retry_exhausted")  # noqa: TRY003

    async def _call_once(
        self,
        *,
        messages: list[ChatCompletionMessageParam],
        attempt: int,
        extra_tags: tuple[str, ...],
        temperature: float | None,
        call: AgentCall,
    ) -> str:
        attempt_number = attempt + 1
        started = log_llm_start(
            self.config.agent,
            self.config.run_id,
            self.config.step,
            self.config.model,
            attempt_number,
        )
        try:
            content = await call(
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature(attempt),
                tags=self.tags(attempt_number, extra_tags),
            )
            log_llm_success(
                self.config.agent,
                self.config.run_id,
                self.config.step,
                self.config.model,
                attempt_number,
                started,
            )
            return content
        except Exception as exc:
            log_llm_failure(
                self.config.agent,
                self.config.run_id,
                self.config.step,
                self.config.model,
                attempt_number,
                started,
                exc,
            )
            if self.config.backoff_seconds > 0:
                await anyio.sleep(self.config.backoff_seconds)
            raise

    def temperature(self, attempt: int) -> float:
        return self.config.retry_temperature if attempt > 0 else self.config.base_temperature

    def tags(self, attempt_number: int, extra_tags: tuple[str, ...] = ()) -> list[str]:
        return [
            f"agent:{self.config.agent}",
            f"step:{self.config.step}",
            f"stage:{self.config.step_label}",
            f"run:{self.config.run_id}",
            f"attempt:{attempt_number}",
            *extra_tags,
            "pipeline:oh-my-class",
        ]
