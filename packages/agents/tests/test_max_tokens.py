"""Tests for thinking budget (max_tokens) in packages.agents.llm."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.config.models import MAX_TOKENS
from packages.agents.llm import complete_json_chat
from packages.agents.llm.chat_context import _AGENT_MAX_TOKENS, _DEFAULT_MAX_TOKENS

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


def test_agent_max_tokens_has_all_five_agents():
    expected_agents = {"planner", "researcher", "content_creator", "diagnostician", "reviewer"}
    assert set(_AGENT_MAX_TOKENS.keys()) == expected_agents


def test_agent_max_tokens_are_positive_integers():
    for agent, tokens in _AGENT_MAX_TOKENS.items():
        assert isinstance(tokens, int), f"{agent} max_tokens must be int"
        assert tokens > 0, f"{agent} max_tokens must be positive"


def test_default_max_tokens_is_positive_integer():
    assert isinstance(_DEFAULT_MAX_TOKENS, int)
    assert _DEFAULT_MAX_TOKENS > 0


def test_content_creator_gets_highest_budget():
    assert _AGENT_MAX_TOKENS["content_creator"] >= _AGENT_MAX_TOKENS["planner"]
    assert _AGENT_MAX_TOKENS["content_creator"] >= _AGENT_MAX_TOKENS["researcher"]


def test_config_reads_from_env():
    assert MAX_TOKENS.planner == 8192
    assert MAX_TOKENS.content_creator == 16384
    assert MAX_TOKENS.default == 8192


def _mock_response(content: str = '{"result": "ok"}') -> SimpleNamespace:
    return SimpleNamespace(
        id="resp-1",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, reasoning_content=None, reasoning=None),
            ),
        ],
        usage=SimpleNamespace(
            model_dump=lambda: {"prompt_tokens": 10, "completion_tokens": 5},
            prompt_tokens=10,
            completion_tokens=5,
        ),
    )


def _messages(content: str = "hello") -> list[ChatCompletionMessageParam]:
    return [{"role": "user", "content": content}]


class _MockStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def __aiter__(self):
        for chunk in self._chunks:
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=chunk),
                    ),
                ],
            )


_EVENT_PATCHER = patch("packages.agents.events.emit_run_event")


@pytest.mark.asyncio
async def test_complete_json_chat_passes_max_tokens_to_api():
    mock_create = AsyncMock(return_value=_mock_response())

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, _EVENT_PATCHER:
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages()

        await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["agent:planner", "run:r1", "attempt:1"],
        )

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == _AGENT_MAX_TOKENS["planner"]


@pytest.mark.asyncio
async def test_explicit_max_tokens_overrides_agent_default():
    mock_create = AsyncMock(return_value=_mock_response())

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, _EVENT_PATCHER:
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages()

        await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["agent:planner", "run:r1", "attempt:1"],
            max_tokens=2048,
        )

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 2048


@pytest.mark.asyncio
async def test_unknown_agent_uses_default_max_tokens():
    mock_create = AsyncMock(return_value=_mock_response())

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, _EVENT_PATCHER:
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages()

        await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["agent:unknown_agent", "run:r1", "attempt:1"],
        )

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == _DEFAULT_MAX_TOKENS


@pytest.mark.asyncio
async def test_content_creator_uses_streaming_transport():
    mock_create = AsyncMock(return_value=_MockStream(['{"result": ', '"ok"}']))

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, _EVENT_PATCHER:
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages()

        result = await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["agent:content_creator", "run:r1", "attempt:1"],
        )

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("stream") is True
        assert call_kwargs.kwargs.get("max_tokens") == _AGENT_MAX_TOKENS["content_creator"]
        assert result == '{"result": "ok"}'


@pytest.mark.asyncio
async def test_no_agent_tag_uses_default_max_tokens():
    mock_create = AsyncMock(return_value=_mock_response())

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, _EVENT_PATCHER:
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages()

        await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["run:r1", "attempt:1"],
        )

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == _DEFAULT_MAX_TOKENS


@pytest.mark.asyncio
async def test_emits_llm_call_started_and_completed_events():
    mock_create = AsyncMock(return_value=_mock_response("hello"))
    events: list[tuple[str, dict[str, object]]] = []

    def capture_event(rid: str, etype: str, data: dict[str, object]) -> None:
        events.append((etype, data))

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, \
         patch("packages.agents.events.emit_run_event", side_effect=capture_event):
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages("test")

        await complete_json_chat(
            model="test-model",
            messages=messages,
            temperature=0.5,
            tags=["agent:planner", "run:r1", "attempt:1"],
        )

    event_types = [e[0] for e in events]
    assert "llm_call_started" in event_types
    assert "llm_call_completed" in event_types


@pytest.mark.asyncio
async def test_emits_llm_call_failed_on_exception():
    mock_create = AsyncMock(side_effect=ValueError("connection timeout"))
    events: list[tuple[str, dict[str, object]]] = []

    def capture_event(rid: str, etype: str, data: dict[str, object]) -> None:
        events.append((etype, data))

    with patch("packages.agents.llm.chat.AsyncOpenAI") as mock_cls, \
         patch("packages.agents.events.emit_run_event", side_effect=capture_event):
        mock_cls.return_value.chat.completions.create = mock_create
        messages = _messages("test")

        with pytest.raises(ValueError, match="connection timeout"):
            await complete_json_chat(
                model="test-model",
                messages=messages,
                temperature=0.5,
                tags=["agent:planner", "run:r1", "attempt:1"],
            )

    event_types = [e[0] for e in events]
    assert "llm_call_started" in event_types
    assert "llm_call_failed" in event_types
    failed_event = next(d for et, d in events if et == "llm_call_failed")
    assert failed_event["error_type"] == "timeout"
