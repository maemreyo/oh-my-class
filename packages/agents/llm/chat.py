from __future__ import annotations

import time
from typing import TYPE_CHECKING, Final

from openai import OpenAIError

from packages.agents.llm.chat_context import CallContext, TransportResult, build_call_context
from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.observability import trace_llm_call
from packages.llm_client.client import ChatMessage, LLMClient

if TYPE_CHECKING:
    import logging

    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )

import logging

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
            "llm.client.request model=%s message_count=%s message_chars=%s tags=%s",
            context.request_model,
            len(messages),
            context.message_chars,
            tags,
        )
        return await _complete_with_trace(messages, temperature, context)
    except (OpenAIError, ValueError) as exc:
        emit_run_event(context.run_id, "llm_call_failed", context.failed_event(exc))
        raise


def chat_messages(system: str, user: str) -> list[ChatCompletionMessageParam]:
    system_message: ChatCompletionSystemMessageParam = {"role": "system", "content": system}
    user_message: ChatCompletionUserMessageParam = {"role": "user", "content": user}
    return [system_message, user_message]


async def _complete_with_trace(
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    context: CallContext,
) -> str:
    from packages.agents.events import emit_run_event

    with trace_llm_call(
        context.agent_name,
        context.run_id,
        context.request_model,
        context.step,
    ) as trace:
        result = await _complete_transport(messages, temperature, context)
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
        emit_run_event(context.run_id, "cost_accrued", context.cost_event(result))
        return result.content


async def _complete_transport(
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    context: CallContext,
) -> TransportResult:
    client = LLMClient()
    llm_messages = [_chat_message(message) for message in messages]
    if context.decision.transport == "streaming":
        # This caller only ever consumes the fully-accumulated text (never
        # individual chunks), so it must get the same before_call/after_call
        # safety pipeline as chat() — chat_via_streaming_transport() runs that
        # pipeline around a streaming HTTP transport. Plain stream() skips
        # after_call by design (see its docstring) and must not be used here.
        result = await client.chat_via_streaming_transport(
            context.request_model,
            llm_messages,
            agent=context.agent_name,
            task=context.task_name,
            run_id=context.run_id,
            step=context.step,
            max_tokens=context.max_tokens,
            temperature=temperature,
        )
        return TransportResult(
            result.content,
            {"prompt_tokens": result.input_tokens, "completion_tokens": result.output_tokens},
            1,
            "stream",
            result.model,
        )
    result = await client.chat(
        context.request_model,
        llm_messages,
        agent=context.agent_name,
        task=context.task_name,
        run_id=context.run_id,
        step=context.step,
        max_tokens=context.max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return TransportResult(
        result.content,
        {"prompt_tokens": result.input_tokens, "completion_tokens": result.output_tokens},
        1,
        "llm_client",
        result.model,
    )


def _chat_message(message: ChatCompletionMessageParam) -> ChatMessage:
    content = message.get("content")
    return ChatMessage(
        role=str(message.get("role", "user")),
        content=content if isinstance(content, str) else str(content),
    )
