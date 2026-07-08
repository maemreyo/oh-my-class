from __future__ import annotations

from types import SimpleNamespace

import openai
import pytest

from packages.llm_client.circuit_breaker import breaker_for
from packages.llm_client.client import ChatMessage, LLMClient, ProviderCircuitOpenError
from packages.llm_client.config import LLMClientConfig
from packages.llm_client.errors import LLMProviderError


class SharedStore:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, float | int | str]] = {}

    def get(self, key: str) -> dict[str, float | int | str] | None:
        return self.values.get(key)

    def set(self, key: str, value: dict[str, float | int | str], _ttl_seconds: float) -> None:
        self.values[key] = value


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
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    breaker_module._provider_store = SharedStore()
    client = LLMClient()
    client._client = _FailingOpenAIClient()

    with pytest.raises(LLMProviderError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )
    with pytest.raises(LLMProviderError):
        await client.chat(
            "flaky-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )
    with pytest.raises(LLMProviderError):
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
async def test_chat_classifies_rate_limit_as_transient_provider_error() -> None:
    """LLMClient.chat must classify real provider errors, not bare-reraise
    openai.OpenAIError — a rate-limit/timeout/connection failure must come
    out as a TransientProviderError so services/gateway/teaching_pack_worker.py
    can requeue it instead of failing the run outright."""
    from packages.llm_client.circuit_breaker import _breakers
    from packages.llm_client.errors import TransientProviderError

    _breakers.clear()
    client = LLMClient()
    client._client = _RateLimitedOpenAIClient()

    with pytest.raises(TransientProviderError):
        await client.chat(
            "rate-limited-provider",
            [ChatMessage(role="user", content="hello")],
            agent="planner",
            task="content_generation",
        )


@pytest.mark.anyio
async def test_stream_success_closes_half_open_provider_circuit() -> None:
    from packages.llm_client.circuit_breaker import _breakers
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    store = SharedStore()
    breaker_module._provider_store = store
    breaker = breaker_for("recovering-provider")
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    store.values["cb:provider:recovering-provider"]["last_failure_time"] = 0.0

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


@pytest.mark.anyio
async def test_chat_via_streaming_transport_runs_after_call_on_joined_content() -> None:
    """A PII pattern split across two chunks must still be scrubbed.

    Proves after_call runs on the fully-accumulated text (not per-chunk,
    which would miss patterns spanning a chunk boundary — the exact bug
    plain stream() has by design, see its docstring).
    """
    client = LLMClient()
    client._client = _PiiSplitAcrossChunksClient()

    result = await client.chat_via_streaming_transport(
        "test-model",
        [ChatMessage(role="user", content="hello")],
        agent="planner",
        task="content_generation",
    )

    assert result.content == "Contact [redacted-pii] for help"


def test_provider_breaker_state_is_shared_through_store() -> None:
    from packages.llm_client.circuit_breaker import _breakers
    import packages.llm_client.circuit_breaker as breaker_module

    _breakers.clear()
    breaker_module._provider_store = SharedStore()
    first_worker = breaker_for("shared-provider")
    first_worker.record_failure()
    first_worker.record_failure()
    first_worker.record_failure()
    _breakers.clear()

    assert breaker_for("shared-provider").is_open() is True


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


class _PiiSplitAcrossChunksCompletions:
    async def create(self, **_kwargs):
        async def stream():
            yield SimpleNamespace(
                model="test-model",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Contact john@ex"))],
                usage=None,
            )
            yield SimpleNamespace(
                model="test-model",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ample.com for help"))],
                usage=None,
            )
            yield SimpleNamespace(
                model="test-model",
                choices=[],
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=7),
            )

        return stream()


class _PiiSplitAcrossChunksClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_PiiSplitAcrossChunksCompletions())


class _RateLimitedCompletions:
    async def create(self, **_kwargs):
        import httpx

        response = httpx.Response(429, request=httpx.Request("POST", "http://test/v1/chat/completions"))
        raise openai.RateLimitError("rate limited", response=response, body=None)


class _RateLimitedOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_RateLimitedCompletions())
