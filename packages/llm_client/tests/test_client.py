from __future__ import annotations

from types import SimpleNamespace

import openai
import pytest

from packages.llm_client.circuit_breaker import breaker_for
from packages.llm_client.client import ChatMessage, LLMClient, ProviderCircuitOpenError
from packages.llm_client.config import LLMClientConfig


def test_config_reads_from_centralized_llm_config() -> None:
    config = LLMClientConfig()
    assert config.base_url == "http://localhost:20228/v1"
    assert config.timeout_s == 600.0
    assert config.max_retries == 3
    assert config.temperature == 0.1


def test_config_uses_llm_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")

    from importlib import reload

    import packages.llm_client.config as llm_client_config

    reload(llm_client_config)

    from packages.llm_client.config import LLMClientConfig

    config = LLMClientConfig()
    assert config.base_url == "http://litellm:4000"
    assert config.api_key == "sk-test-key"


@pytest.mark.anyio
async def test_chat_records_provider_failure_and_skips_open_circuit() -> None:
    from packages.llm_client.circuit_breaker import _breakers

    _breakers.clear()
    client = LLMClient()
    client._client = _FailingOpenAIClient()

    with pytest.raises(openai.OpenAIError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )
    with pytest.raises(openai.OpenAIError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )
    with pytest.raises(openai.OpenAIError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )

    assert breaker_for("flaky-provider").is_open() is True
    with pytest.raises(ProviderCircuitOpenError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )
    assert client._client.calls == 3


@pytest.mark.anyio
async def test_stream_success_closes_half_open_provider_circuit() -> None:
    from packages.llm_client.circuit_breaker import _breakers

    _breakers.clear()
    breaker = breaker_for("recovering-provider")
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    breaker._opened_at = 0.0

    client = LLMClient()
    client._client = _StreamingOpenAIClient()

    chunks = [chunk async for chunk in client.stream(
        "recovering-provider",
        [ChatMessage(role="user", content="hello")],
        agent="planner",
        task="content_generation",
    )]

    assert chunks == ["ok"]
    assert breaker_for("recovering-provider").is_open() is False


class _FailingCompletions:
    def __init__(self) -> None:
        self.calls = 0

    async def create(self, **_kwargs):
        self.calls += 1
        raise openai.OpenAIError("provider down")


class _FailingOpenAIClient:
    def __init__(self) -> None:
        completions = _FailingCompletions()
        self.chat = SimpleNamespace(completions=completions)
        self._completions = completions

    @property
    def calls(self) -> int:
        return self._completions.calls


class _StreamingCompletions:
    async def create(self, **_kwargs):
        async def stream():
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))])

        return stream()


class _StreamingOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_StreamingCompletions())
