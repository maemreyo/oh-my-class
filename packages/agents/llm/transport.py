from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.llm_client.client import AsyncOpenAI, ChatCompletionMessageParam


def metadata(tags: list[str]) -> dict[str, list[str]]:
    return {"tags": tags}


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
