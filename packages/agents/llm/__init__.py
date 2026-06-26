from __future__ import annotations

import json as _json
import logging
import time
from typing import TYPE_CHECKING, Any, Final

from openai import AsyncOpenAI

from packages.agents.config.models import LLM

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
        str(error)[:500],
    )


async def complete_json_chat(
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
) -> str:
    started = time.monotonic()
    request_model = model.removeprefix("openai/")
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
    response = await client.chat.completions.create(
        model=request_model,
        messages=messages,
        temperature=temperature,
        extra_body={"metadata": "|".join(tags) if tags else ""},
    )
    usage = response.usage.model_dump() if response.usage is not None else None
    choice_count = len(response.choices)
    _LOGGER.info(
        "llm.transport.response model=%s response_id=%s response_model=%s "
        "choices=%s usage=%s duration_s=%.1f",
        request_model,
        response.id,
        response.model,
        choice_count,
        usage,
        time.monotonic() - started,
    )
    if not response.choices:
        _LOGGER.warning(
            "llm.transport.empty_choices model=%s response_id=%s response_model=%s usage=%s",
            request_model,
            response.id,
            response.model,
            usage,
        )
        raise RuntimeError(
            f"9Router returned empty choices for model={model}; response_id={response.id}"
        )
    choice = response.choices[0]
    content = choice.message.content or ""
    if not content:
        # Reasoning models sometimes put content in the reasoning field
        msg = choice.message
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
        if reasoning:
            if isinstance(reasoning, list):
                content = "".join(p.get("text", str(p)) if isinstance(p, dict) else str(p) for p in reasoning)  # noqa: E501
            else:
                content = str(reasoning)
            _LOGGER.info(
                "llm.transport.fallback_from_reasoning model=%s response_id=%s fallback_chars=%s",
                request_model,
                response.id,
                len(content),
            )
    return content


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
