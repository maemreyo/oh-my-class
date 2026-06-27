from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Final

from openai import AsyncOpenAI, OpenAIError

from packages.agents.config.models import LLM
from packages.agents.llm.chat_context import CallContext, TransportResult, build_call_context
from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.llm.transport import complete_non_streaming_chat, complete_streaming_chat
from packages.agents.observability import trace_llm_call

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )

_LOGGER: Final = logging.getLogger("packages.agents.llm")


def log_llm_start(agent: str, run_id: str, step: int, model: str, attempt: int) -> float:
    started = time.monotonic()
    _LOGGER.info(
        "llm.call.start agent=%s run_id=%s step=%s model=%s attempt=%s",
        agent,
        run_id,
        step,
        model,
        attempt,
    )
    return started


def log_llm_success(
    agent: str,
    run_id: str,
    step: int,
    model: str,
    attempt: int,
    started: float,
) -> None:
    _LOGGER.info(
        "llm.call.success agent=%s run_id=%s step=%s model=%s attempt=%s duration_s=%.1f",
        agent,
        run_id,
        step,
        model,
        attempt,
        time.monotonic() - started,
    )


def log_llm_failure(
    agent: str,
    run_id: str,
    step: int,
    model: str,
    attempt: int,
    started: float,
    error: BaseException,
) -> None:
    _LOGGER.warning(
        "llm.call.failure agent=%s run_id=%s step=%s model=%s attempt=%s duration_s=%.1f error=%s",
        agent,
        run_id,
        step,
        model,
        attempt,
        time.monotonic() - started,
        safe_error_summary(error),
    )


async def complete_json_chat(
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
    max_tokens: int | None = None,
) -> str:
    from packages.agents.events import emit_run_event

    context = build_call_context(model, messages, tags, max_tokens)

    try:
        context.enforce_prompt_gate(messages)
        emit_run_event(context.run_id, "llm_call_started", context.started_event)
        _LOGGER.info(
            "llm.transport.request model=%s base_url=%s message_count=%s message_chars=%s tags=%s",
            context.request_model,
            LLM.base_url,
            len(messages),
            context.message_chars,
            tags,
        )
        client = AsyncOpenAI(
            api_key=LLM.api_key or "no-key",
            base_url=LLM.base_url,
            timeout=LLM.timeout,
            max_retries=LLM.max_retries,
        )
        return await _complete_with_trace(client, messages, temperature, tags, context)
    except (OpenAIError, ValueError) as exc:
        emit_run_event(context.run_id, "llm_call_failed", context.failed_event(exc))
        raise


def chat_messages(system: str, user: str) -> list[ChatCompletionMessageParam]:
    system_message: ChatCompletionSystemMessageParam = {"role": "system", "content": system}
    user_message: ChatCompletionUserMessageParam = {"role": "user", "content": user}
    return [system_message, user_message]


async def _complete_with_trace(
    client: AsyncOpenAI,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
    context: CallContext,
) -> str:
    from packages.agents.events import emit_run_event

    with trace_llm_call(
        context.agent_name,
        context.run_id,
        context.request_model,
        context.step,
    ) as trace:
        result = await _complete_transport(client, messages, temperature, tags, context)
        _LOGGER.info(
            "llm.transport.response model=%s response_id=%s response_model=%s "
            "choices=%s usage=%s duration_s=%.1f",
            context.request_model,
            result.response_id,
            result.response_model,
            result.choice_count,
            result.usage,
            time.monotonic() - context.started,
        )
        trace.update(
            input=context.trace_input(messages, temperature),
            output={"content_length": len(result.content), "choice_count": result.choice_count},
            usage=result.usage,
            metadata=context.trace_metadata(result),
        )
        emit_run_event(context.run_id, "llm_call_completed", context.completed_event(result))
        return result.content


async def _complete_transport(
    client: AsyncOpenAI,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
    context: CallContext,
) -> TransportResult:
    if context.decision.transport == "streaming":
        content = await complete_streaming_chat(
            client,
            context.request_model,
            messages,
            temperature,
            context.max_tokens,
            tags,
        )
        return TransportResult(content, None, 1, "stream", context.request_model)
    result = await complete_non_streaming_chat(
        client,
        context.request_model,
        messages,
        temperature,
        context.max_tokens,
        tags,
    )
    return TransportResult(
        result.content,
        result.usage,
        result.choice_count,
        result.response_id,
        result.response_model,
    )
