"""MockLLMClient — deterministic fake for agent tests.

No network calls, no API keys needed. Inject in place of LLMClient.
"""
from __future__ import annotations

from collections import defaultdict
from typing import AsyncIterator

from packages.llm_client.client import ChatMessage, ChatResponse


class MockLLMClient:
    """Fake LLMClient for testing.

    Usage:
        mock = MockLLMClient()
        mock.set_response("f.pro", "content_generation", '{"sections": [...]}')
        result = await mock.chat("f.pro", messages, task="content_generation")
        assert mock.call_count("f.pro") == 1
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], list[str]] = defaultdict(list)
        self._calls: list[dict] = []
        self._default_response = '{"result": "mock response"}'

    def set_response(self, model: str, task: str, response: str) -> None:
        """Queue a response for a specific model+task combo."""
        self._responses[(model, task)].append(response)

    def set_default(self, response: str) -> None:
        """Fallback response when no specific response is queued."""
        self._default_response = response

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        **kwargs,
    ) -> ChatResponse:
        self._calls.append({"model": model, "task": task, "agent": agent, "run_id": run_id})

        queue = self._responses.get((model, task), [])
        content = queue.pop(0) if queue else self._default_response

        return ChatResponse(
            content=content,
            model=model,
            input_tokens=max(1, sum(len(m.content) for m in messages) // 4),
            output_tokens=max(1, len(content) // 4),
        )

    async def stream(
        self,
        model: str,
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        resp = await self.chat(model, messages, agent=agent, task=task, run_id=run_id)
        for word in resp.content.split():
            yield word + " "

    def call_count(self, model: str | None = None, task: str | None = None) -> int:
        calls = self._calls
        if model is not None:
            calls = [c for c in calls if c["model"] == model]
        if task is not None:
            calls = [c for c in calls if c["task"] == task]
        return len(calls)

    def last_call(self) -> dict | None:
        return self._calls[-1] if self._calls else None

    def reset(self) -> None:
        self._calls.clear()
        self._responses.clear()
