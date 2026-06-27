from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionMessageParam

_LOGGER = logging.getLogger("packages.agents.llm.transport")


@dataclass(frozen=True, slots=True)
class ChatResult:
    content: str
    usage: dict[str, Any] | None
    choice_count: int
    response_id: str
    response_model: str


def metadata(tags: list[str]) -> dict[str, list[str]]:
    return {"tags": tags}


async def complete_non_streaming_chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    max_tokens: int,
    tags: list[str],
) -> ChatResult:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"metadata": metadata(tags)},
    )
    usage = response.usage.model_dump() if response.usage is not None else None
    if not response.choices:
        _LOGGER.warning(
            "llm.transport.empty_choices model=%s response_id=%s response_model=%s usage=%s",
            model,
            response.id,
            response.model,
            usage,
        )
        msg = "9Router returned empty choices for " f"model={model}; response_id={response.id}"
        raise RuntimeError(msg)

    choice = response.choices[0]
    content = choice.message.content or _reasoning_content(choice.message)
    return ChatResult(
        content=content,
        usage=usage,
        choice_count=len(response.choices),
        response_id=response.id,
        response_model=response.model,
    )


async def complete_streaming_chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    max_tokens: int,
    tags: list[str],
) -> str:
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body={"metadata": metadata(tags)},
    )
    chunks: list[str] = []
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            chunks.append(delta)
    return "".join(chunks)


def _reasoning_content(message: Any) -> str:
    reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
    if not reasoning:
        return ""
    if isinstance(reasoning, list):
        content = "".join(
            part.get("text", str(part)) if isinstance(part, dict) else str(part)
            for part in reasoning
        )
    else:
        content = str(reasoning)
    _LOGGER.info("llm.transport.fallback_from_reasoning fallback_chars=%s", len(content))
    return content
