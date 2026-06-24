---
title: "LLM Client: C3 — LLMClient Wrapper, build_tags(), MockLLMClient"
status: ready
labels: [architecture, agents, llm]
created: 2026-06-24
priority: p0
report: "04"
---

## What to build

A `LLMClient` wrapper module that all agents inject and use. Abstracts the underlying endpoint (9Router local or LiteLLM production) behind a single config. `build_tags()` centralizes cost attribution metadata. `MockLLMClient` enables agent testing without any live LLM.

**Design decisions:**
- **C3**: `LLMClient` wraps `openai.AsyncOpenAI`, injected into agents — not instantiated inline
- **CA-A**: `LLM_CLIENT_BASE_URL` env var selects endpoint — no code change between environments
- **FB3**: `LLMClient` does NOT implement fallback logic — that boundary belongs to LiteLLM (infra errors) and `healing_node` (content errors)

## File Structure

```
packages/llm_client/
├── __init__.py
├── client.py           # LLMClient: chat(), stream() — main entry point
├── config.py           # LLMClientConfig(BaseSettings) — base_url, keys, timeouts
├── tags.py             # build_tags(agent, run_id, task) → metadata dict
├── mock.py             # MockLLMClient — deterministic fake for tests
└── tests/
    ├── test_client.py
    ├── test_tags.py
    └── test_mock.py
```

## Implementation Spec

### `llm_client/config.py`

```python
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMClientConfig(BaseSettings):
    """LLM client configuration.

    Local dev:  LLM_CLIENT_BASE_URL=http://localhost:20128  (9Router direct)
    Production: LLM_CLIENT_BASE_URL=http://litellm:4000    (LiteLLM layer)

    Agents never need to know which one is active.
    """
    model_config = SettingsConfigDict(
        env_prefix="LLM_CLIENT_",
        env_file=".env",
        extra="ignore",
    )

    base_url: str = "http://localhost:20128"   # default: 9Router local
    api_key: str = "dummy"                     # 9Router accepts any key locally
    timeout_s: float = 120.0
    max_retries: int = 0    # 0 = no client-side retry (LiteLLM handles retries in prod)
    temperature: float = 0.1
```

### `llm_client/tags.py`

```python
"""Cost attribution metadata tags.

All agent calls include these tags — LiteLLM logs them for per-agent cost tracking.
9Router silently ignores the metadata field (OpenAI-compatible extra_body).
"""
from __future__ import annotations


def build_tags(
    agent: str,
    task: str,
    run_id: str | None = None,
) -> dict:
    """Build metadata tags dict for LiteLLM cost attribution.

    Args:
        agent: agent name, e.g. "content_creator", "llm_judge"
        task:  task type, e.g. "content_generation", "fact_verification"
        run_id: graph run ID for per-run cost breakdown

    Returns metadata dict passed as extra_body to LLM calls.
    """
    tags = [
        f"agent:{agent}",
        f"task:{task}",
        "pipeline:oh-my-class",
    ]
    if run_id:
        tags.append(f"run_id:{run_id}")

    return {"metadata": {"tags": tags}}
```

### `llm_client/client.py`

```python
"""LLMClient: thin wrapper over openai.AsyncOpenAI.

All agents receive an LLMClient instance via dependency injection.
Never instantiate openai.AsyncOpenAI directly inside agent code.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import AsyncIterator
import openai

from packages.llm_client.config import LLMClientConfig
from packages.llm_client.tags import build_tags


@dataclass
class ChatMessage:
    role: str     # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cached: bool = False


class LLMClient:
    """Wrapper over openai.AsyncOpenAI pointed at configured endpoint.

    Local:      base_url = http://localhost:20128 (9Router)
    Production: base_url = http://litellm:4000   (LiteLLM)

    Both expose OpenAI-compatible API — client code is identical.
    """

    def __init__(self, config: LLMClientConfig | None = None):
        self._config = config or LLMClientConfig()
        self._client = openai.AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout_s,
            max_retries=self._config.max_retries,
        )

    async def chat(
        self,
        model: str,                          # "f.light" | "f.pro" — always
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> ChatResponse:
        """Send chat request. Returns ChatResponse with usage stats."""
        extra = build_tags(agent, task, run_id)

        kwargs: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature ?? self._config.temperature,
            "extra_body": extra,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()

        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cached=getattr(usage, "cached_tokens", 0) > 0,
        )

    async def stream(
        self,
        model: str,
        messages: list[ChatMessage],
        agent: str = "unknown",
        task: str = "unknown",
        run_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat response token by token."""
        extra = build_tags(agent, task, run_id)
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=self._config.temperature,
            extra_body=extra,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
```

### `llm_client/mock.py`

```python
"""MockLLMClient — deterministic fake for agent tests.

No network calls, no API keys needed. Inject in place of LLMClient.
"""
from __future__ import annotations
from collections import defaultdict
from packages.llm_client.client import ChatMessage, ChatResponse


class MockLLMClient:
    """Fake LLMClient for testing.

    Usage:
        mock = MockLLMClient()
        mock.set_response("f.pro", "content_generation", '{"sections": [...]}')
        result = await mock.chat("f.pro", messages, task="content_generation")
        assert mock.call_count("f.pro") == 1
    """

    def __init__(self):
        self._responses: dict[tuple[str, str], list[str]] = defaultdict(list)
        self._calls: list[dict] = []
        self._default_response = '{"result": "mock response"}'

    def set_response(self, model: str, task: str, response: str) -> None:
        """Queue a response for a specific model+task combo."""
        self._responses[(model, task)].append(response)

    def set_default(self, response: str) -> None:
        """Fallback response when no specific response queued."""
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
            input_tokens=len(" ".join(m.content for m in messages)) // 4,
            output_tokens=len(content) // 4,
        )

    async def stream(self, model: str, messages: list[ChatMessage], **kwargs):
        resp = await self.chat(model, messages, **kwargs)
        for word in resp.content.split():
            yield word + " "

    def call_count(self, model: str | None = None, task: str | None = None) -> int:
        calls = self._calls
        if model:
            calls = [c for c in calls if c["model"] == model]
        if task:
            calls = [c for c in calls if c["task"] == task]
        return len(calls)

    def last_call(self) -> dict | None:
        return self._calls[-1] if self._calls else None

    def reset(self) -> None:
        self._calls.clear()
        self._responses.clear()
```

### Usage in agent nodes

```python
# packages/agents/content_creator/node.py

from packages.llm_client.client import LLMClient, ChatMessage
from packages.agents.config import MODELS

async def content_creator_node(
    state: OhMyClassState,
    llm: LLMClient | None = None,   # injected — defaults to real client
) -> dict:
    llm = llm or LLMClient()

    response = await llm.chat(
        model=MODELS.content_generation,   # "f.pro"
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ],
        agent="content_creator",
        task="content_generation",
        run_id=state.get("run_id"),
    )
    ...
```

## Tests

```python
# tests/test_client.py

import pytest
from packages.llm_client.mock import MockLLMClient
from packages.llm_client.client import ChatMessage
from packages.llm_client.tags import build_tags

async def test_mock_returns_set_response():
    mock = MockLLMClient()
    mock.set_response("f.pro", "content_generation", '{"title": "Test Lesson"}')
    resp = await mock.chat(
        "f.pro",
        [ChatMessage(role="user", content="generate")],
        task="content_generation",
    )
    assert resp.content == '{"title": "Test Lesson"}'

async def test_mock_tracks_call_count():
    mock = MockLLMClient()
    await mock.chat("f.light", [ChatMessage(role="user", content="x")], task="summarize")
    await mock.chat("f.light", [ChatMessage(role="user", content="y")], task="summarize")
    assert mock.call_count("f.light") == 2
    assert mock.call_count("f.pro") == 0

async def test_mock_last_call():
    mock = MockLLMClient()
    await mock.chat("f.pro", [ChatMessage(role="user", content="x")],
                   agent="llm_judge", task="quality_gate", run_id="run-1")
    call = mock.last_call()
    assert call["agent"] == "llm_judge"
    assert call["run_id"] == "run-1"

def test_build_tags_structure():
    tags = build_tags("content_creator", "content_generation", "run-123")
    assert "metadata" in tags
    assert "agent:content_creator" in tags["metadata"]["tags"]
    assert "task:content_generation" in tags["metadata"]["tags"]
    assert "run_id:run-123" in tags["metadata"]["tags"]
    assert "pipeline:oh-my-class" in tags["metadata"]["tags"]

def test_build_tags_no_run_id():
    tags = build_tags("llm_judge", "quality_gate")
    assert not any(t.startswith("run_id:") for t in tags["metadata"]["tags"])
```

## Acceptance Criteria

- [ ] `LLMClientConfig` reads `LLM_CLIENT_BASE_URL` — defaults to 9Router local
- [ ] `LLMClient.chat()` uses model names `"f.light"` / `"f.pro"` — no provider names
- [ ] `LLMClient.chat()` always appends `build_tags()` in `extra_body`
- [ ] `MockLLMClient.set_response(model, task, content)` queues deterministic responses
- [ ] `MockLLMClient.call_count()` tracks calls by model/task
- [ ] All agent node tests use `MockLLMClient` — zero real LLM calls
- [ ] `LLMClient` does NOT implement fallback/retry (that's LiteLLM's job)
- [ ] Switching local→production = change 1 env var, zero code change

## Dependencies

- Blocked by: `gate-config` (MODELS.content_generation = "f.pro" naming)
- Blocks: all agent node implementations (content_creator, llm_judge, fact_verification, etc.)
- Priority: p0 — foundational for all agent testing
