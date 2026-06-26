"""Shared LLM client for all agents.

Routes directly to 9Router in development.
"""

from __future__ import annotations

import json as _json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Final

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )

NINEROUTER_BASE_URL: Final = "http://localhost:20128/v1"
_LOGGER: Final = logging.getLogger("packages.agents.llm")

MODEL_COMBO_MAP: Final[dict[str, str]] = {
    "f.light": "openai/f.pro",
    "f.pro": "openai/f.pro",
    "gpt-5.4": "openai/f.pro",
    "deepseek-v4-flash": "openai/f.pro",
    "deepseek-free": "openai/f.pro",
    "content-fusion": "openai/f.pro",
    "deepseek-compressed": "openai/f.pro",
    "deepseek-direct": "openai/f.pro",
}


def get_llm_config() -> dict[str, Any]:
    """Get LLM configuration from environment.

    Development routes directly to 9Router; LiteLLM is intentionally bypassed.
    """
    nine_router_key = os.environ.get("NINEROUTER_API_KEY", "")
    return {
        "api_base": os.environ.get("NINEROUTER_BASE_URL", NINEROUTER_BASE_URL),
        "api_key": nine_router_key,
    }


def resolve_model(combo_name: str) -> str:
    """Resolve a 9Router combo name to an litellm-compatible model string.

    Examples:
        "f.light" → "openai/f.pro"
        "deepseek-v4-flash" → "openai/f.pro"
        "gpt-5.4" → "openai/f.pro"
    """
    return MODEL_COMBO_MAP.get(combo_name, "openai/f.pro")


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
    config = get_llm_config()
    started = time.monotonic()
    request_model = model.removeprefix("openai/")
    _LOGGER.info(
        "llm.transport.request model=%s base_url=%s message_count=%s message_chars=%s tags=%s",
        request_model,
        config["api_base"],
        len(messages),
        _message_chars(messages),
        tags,
    )
    client = AsyncOpenAI(
        api_key=config["api_key"] or "no-key",
        base_url=config["api_base"],
        timeout=120.0,
        max_retries=0,
    )
    response = await client.chat.completions.create(
        model=request_model,
        messages=messages,
        temperature=temperature,
        extra_body={"metadata": {"tags": tags}},
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
    return choice.message.content or ""


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
