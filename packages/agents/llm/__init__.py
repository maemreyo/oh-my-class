"""Shared LLM client for all agents.

Routes directly to 9Router in development.
"""

from __future__ import annotations

import json as _json
import logging
import os
import time
from typing import Any, Final

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

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
    messages: list[dict[str, str]],
    temperature: float,
    tags: list[str],
) -> str:
    config = get_llm_config()
    client = AsyncOpenAI(
        api_key=config["api_key"] or "no-key",
        base_url=config["api_base"],
        timeout=300.0,
        max_retries=2,
    )
    typed_messages: list[ChatCompletionMessageParam] = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
    ]
    response = await client.chat.completions.create(
        model=model.removeprefix("openai/"),
        messages=typed_messages,
        temperature=temperature,
        extra_body={"metadata": {"tags": tags}},
    )
    choice = response.choices[0]
    return choice.message.content or ""


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
