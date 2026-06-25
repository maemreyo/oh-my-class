"""Tests for MockLLMClient — deterministic fake for agent tests."""
from __future__ import annotations

import pytest

from packages.llm_client.client import ChatMessage
from packages.llm_client.mock import MockLLMClient


@pytest.mark.asyncio
async def test_mock_returns_default_response():
    mock = MockLLMClient()
    resp = await mock.chat("f.pro", [ChatMessage(role="user", content="test")], task="something")
    assert resp.content == '{"result": "mock response"}'


@pytest.mark.asyncio
async def test_mock_returns_set_response():
    mock = MockLLMClient()
    mock.set_response("f.pro", "content_generation", '{"title": "Test Lesson"}')
    resp = await mock.chat(
        "f.pro",
        [ChatMessage(role="user", content="generate")],
        task="content_generation",
    )
    assert resp.content == '{"title": "Test Lesson"}'


@pytest.mark.asyncio
async def test_mock_queued_responses_consumed_in_order():
    mock = MockLLMClient()
    mock.set_response("f.pro", "content_generation", "first")
    mock.set_response("f.pro", "content_generation", "second")
    r1 = await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="content_generation")  # noqa: E501
    r2 = await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="content_generation")  # noqa: E501
    assert r1.content == "first"
    assert r2.content == "second"


@pytest.mark.asyncio
async def test_mock_falls_back_to_default_when_queue_empty():
    mock = MockLLMClient()
    mock.set_response("f.pro", "content_generation", "queued")
    await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="content_generation")
    # Queue empty — falls back to default
    resp = await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="content_generation")  # noqa: E501
    assert resp.content == '{"result": "mock response"}'


@pytest.mark.asyncio
async def test_mock_tracks_call_count_by_model():
    mock = MockLLMClient()
    await mock.chat("f.light", [ChatMessage(role="user", content="x")], task="summarize")
    await mock.chat("f.light", [ChatMessage(role="user", content="y")], task="summarize")
    assert mock.call_count("f.light") == 2
    assert mock.call_count("f.pro") == 0


@pytest.mark.asyncio
async def test_mock_tracks_call_count_by_task():
    mock = MockLLMClient()
    await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="content_generation")
    await mock.chat("f.pro", [ChatMessage(role="user", content="y")], task="quality_gate")
    assert mock.call_count(task="content_generation") == 1
    assert mock.call_count(task="quality_gate") == 1


@pytest.mark.asyncio
async def test_mock_total_call_count():
    mock = MockLLMClient()
    await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="t1")
    await mock.chat("f.light", [ChatMessage(role="user", content="y")], task="t2")
    assert mock.call_count() == 2


@pytest.mark.asyncio
async def test_mock_last_call():
    mock = MockLLMClient()
    await mock.chat(
        "f.pro",
        [ChatMessage(role="user", content="x")],
        agent="llm_judge",
        task="quality_gate",
        run_id="run-1",
    )
    call = mock.last_call()
    assert call is not None
    assert call["agent"] == "llm_judge"
    assert call["task"] == "quality_gate"
    assert call["run_id"] == "run-1"
    assert call["model"] == "f.pro"


def test_mock_last_call_none_when_empty():
    mock = MockLLMClient()
    assert mock.last_call() is None


@pytest.mark.asyncio
async def test_mock_reset_clears_state():
    mock = MockLLMClient()
    mock.set_response("f.pro", "task", "value")
    await mock.chat("f.pro", [ChatMessage(role="user", content="x")], task="task")
    mock.reset()
    assert mock.call_count() == 0
    assert mock.last_call() is None


@pytest.mark.asyncio
async def test_mock_set_default_changes_fallback():
    mock = MockLLMClient()
    mock.set_default("custom default")
    resp = await mock.chat("f.light", [ChatMessage(role="user", content="x")], task="anything")
    assert resp.content == "custom default"


@pytest.mark.asyncio
async def test_mock_stream_yields_words():
    mock = MockLLMClient()
    mock.set_default("hello world foo")
    chunks = []
    async for chunk in mock.stream("f.light", [ChatMessage(role="user", content="x")]):
        chunks.append(chunk)
    assert len(chunks) == 3
    assert "".join(chunks).strip() == "hello world foo"


@pytest.mark.asyncio
async def test_mock_chat_returns_token_estimates():
    mock = MockLLMClient()
    resp = await mock.chat(
        "f.pro",
        [ChatMessage(role="user", content="hello world")],
        task="content_generation",
    )
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.model == "f.pro"
