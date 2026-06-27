from __future__ import annotations

import json as _json
import logging
import time
from typing import TYPE_CHECKING, Any, Final

from openai import AsyncOpenAI

from packages.agents.config.models import LLM, MAX_TOKENS
from packages.agents.llm.transport import complete_non_streaming_chat, complete_streaming_chat
from packages.agents.observability import trace_llm_call

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )

_LOGGER: Final = logging.getLogger("packages.agents.llm")

# Per-agent max_tokens defaults — caps total output (thinking + content)
# so reasoning models can't burn unlimited tokens on reasoning.
# Configured via MAX_TOKENS_* env vars (see packages/agents/config/models.py).
_AGENT_MAX_TOKENS: dict[str, int] = {
    "planner": MAX_TOKENS.planner,
    "researcher": MAX_TOKENS.researcher,
    "content_creator": MAX_TOKENS.content_creator,
    "diagnostician": MAX_TOKENS.diagnostician,
    "reviewer": MAX_TOKENS.reviewer,
}
_DEFAULT_MAX_TOKENS = MAX_TOKENS.default
_STREAMING_AGENTS: Final = {"content_creator"}


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
        str(error)[:500],
    )


async def complete_json_chat(
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
    max_tokens: int | None = None,
) -> str:
    from packages.agents.events import emit_run_event

    started = time.monotonic()
    request_model = model.removeprefix("openai/")

    run_id = ""
    agent_name = ""
    attempt = 1
    step = 0
    for tag in tags:
        if tag.startswith("run:"):
            run_id = tag.split(":", 1)[1]
        elif tag.startswith("agent:"):
            agent_name = tag.split(":", 1)[1]
        elif tag.startswith("attempt:"):
            attempt = int(tag.split(":", 1)[1])
        elif tag.startswith("step:"):
            step = int(tag.split(":", 1)[1])

    # Resolve max_tokens: explicit > agent-specific default > global default
    if max_tokens is None:
        max_tokens = _AGENT_MAX_TOKENS.get(agent_name, _DEFAULT_MAX_TOKENS)

    emit_run_event(run_id, "llm_call_started", {
        "agent": agent_name,
        "model": request_model,
        "attempt": attempt,
        "max_tokens": max_tokens,
        "message_chars": _message_chars(messages),
    })

    try:
        _LOGGER.info(
            "llm.transport.request model=%s base_url=%s message_count=%s message_chars=%s tags=%s",
            request_model,
            LLM.base_url,
            len(messages),
            _message_chars(messages),
            tags,
        )
        client = AsyncOpenAI(
            api_key=LLM.api_key or "no-key",
            base_url=LLM.base_url,
            timeout=LLM.timeout,
            max_retries=LLM.max_retries,
        )

        with trace_llm_call(agent_name, run_id, request_model, step) as trace:
            use_stream = agent_name in _STREAMING_AGENTS
            if use_stream:
                content = await complete_streaming_chat(
                    client,
                    request_model,
                    messages,
                    temperature,
                    max_tokens,
                    tags,
                )
                usage = None
                choice_count = 1
                response_id = "stream"
                response_model = request_model
            else:
                result = await complete_non_streaming_chat(
                    client,
                    request_model,
                    messages,
                    temperature,
                    max_tokens,
                    tags,
                )
                content = result.content
                usage = result.usage
                choice_count = result.choice_count
                response_id = result.response_id
                response_model = result.response_model
            _LOGGER.info(
                "llm.transport.response model=%s response_id=%s response_model=%s "
                "choices=%s usage=%s duration_s=%.1f",
                request_model,
                response_id,
                response_model,
                choice_count,
                usage,
                time.monotonic() - started,
            )

            trace.update(
                input={
                    "messages": len(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                output={"content_length": len(content), "choice_count": choice_count},
                usage=usage,
                metadata={
                    "attempt": attempt,
                    "response_id": response_id,
                    "response_model": response_model,
                    "stream": use_stream,
                },
            )

            emit_run_event(run_id, "llm_call_completed", {
                "agent": agent_name,
                "model": request_model,
                "attempt": attempt,
                "step": step,
                "duration_s": round(time.monotonic() - started, 1),
                "response_chars": len(content),
                "usage": usage,
            })
            return content
    except Exception as exc:
        error_type = type(exc).__name__.lower()
        exc_str = str(exc).lower()
        if "timeout" in exc_str:
            error_type = "timeout"
        elif "json" in exc_str:
            error_type = "json_parse"
        elif "empty" in exc_str:
            error_type = "empty_response"
        emit_run_event(run_id, "llm_call_failed", {
            "agent": agent_name,
            "model": request_model,
            "attempt": attempt,
            "step": step,
            "duration_s": round(time.monotonic() - started, 1),
            "error": str(exc)[:200],
            "error_type": error_type,
        })
        raise

def chat_messages(system: str, user: str) -> list[ChatCompletionMessageParam]:
    system_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": system,
    }
    user_message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": user,
    }
    return [system_message, user_message]


def _message_chars(messages: list[ChatCompletionMessageParam]) -> int:
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            total += len(str(content))
    return total


def extract_json_text(content: Any, reasoning_content: Any = None) -> str:
    """Extract JSON string from LLM response content.

    Handles: str, dict, list, None — normalizes to a JSON-parseable string.
    Falls back to reasoning_content when content is empty (reasoning models).
    """
    if isinstance(content, (dict, list)):
        return _json.dumps(content)
    text = str(content).strip() if content else ""
    if not text and reasoning_content:
        if isinstance(reasoning_content, list):
            parts = [
                p.get("text", str(p)) if isinstance(p, dict) else str(p)
                for p in reasoning_content
            ]
            text = "".join(parts).strip()
        else:
            text = str(reasoning_content).strip()
    if not text:
        raise ValueError("LLM returned empty content")
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text
