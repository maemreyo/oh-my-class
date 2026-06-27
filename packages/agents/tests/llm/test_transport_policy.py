from __future__ import annotations

from typing import Any

import pytest

from packages.agents.events import clear_run, get_run_events
from packages.agents.llm import chat
from packages.agents.llm.prompt_gate import MAX_PROMPT_CHARS, PromptGateError
from packages.agents.llm.transport import ChatResult
from packages.agents.llm.transport_policy import TransportPolicyInput, decide_transport, prompt_hash


class RecordingTrace:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def __enter__(self) -> RecordingTrace:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)


class TestTransportPolicy:
    def test_streams_long_artifact_generation(self) -> None:
        decision = decide_transport(_payload(agent="content_creator", task="content_generation"))

        assert decision.transport == "streaming"
        assert decision.reason == "streaming_agent"
        assert decision.capture_full_io is False

    def test_keeps_short_judge_non_streaming(self) -> None:
        decision = decide_transport(_payload(agent="reviewer", task="llm_judge"))

        assert decision.transport == "non_streaming"
        assert decision.reason == "short_control_task"

    def test_streams_large_research_prompt(self) -> None:
        decision = decide_transport(_payload(
            agent="researcher",
            task="research_synthesis",
            message_chars=20_000,
        ))

        assert decision.transport == "streaming"
        assert decision.reason == "large_prompt"

    def test_timeout_retry_streams_when_safe(self) -> None:
        decision = decide_transport(_payload(
            attempt=2,
            previous_error_type="timeout",
            safe_to_stream=True,
        ))

        assert decision.transport == "streaming"
        assert decision.reason == "timeout_retry_streaming"

    def test_timeout_retry_stays_non_streaming_when_not_safe(self) -> None:
        decision = decide_transport(_payload(
            attempt=2,
            previous_error_type="timeout",
            safe_to_stream=False,
        ))

        assert decision.transport == "non_streaming"
        assert decision.reason == "default_non_streaming"

    def test_hashes_prompt_without_capturing_text(self) -> None:
        digest = prompt_hash("secret prompt")

        assert len(digest) == 64
        assert "secret" not in digest


@pytest.mark.anyio
async def test_complete_json_chat_records_policy_metadata_without_full_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-transport-metadata"
    secret_prompt = "secret prompt text"
    secret_output = '{"ok": true, "secret": "hidden"}'
    trace = RecordingTrace()

    async def fake_complete_non_streaming_chat(*_args: Any, **_kwargs: Any) -> ChatResult:
        return ChatResult(
            content=secret_output,
            usage={"total_tokens": 12},
            choice_count=1,
            response_id="response-1",
            response_model="deepseek-test",
        )

    monkeypatch.setattr(chat, "complete_non_streaming_chat", fake_complete_non_streaming_chat)
    monkeypatch.setattr(chat, "trace_llm_call", lambda *_args: trace)
    clear_run(run_id)

    result = await chat.complete_json_chat(
        model="openai/deepseek-test",
        messages=chat.chat_messages("system", secret_prompt),
        temperature=0.0,
        tags=["agent:reviewer", f"run:{run_id}", "step:10", "task:llm_judge"],
        max_tokens=256,
    )

    assert result == secret_output
    assert len(trace.updates) == 1
    trace_update = trace.updates[0]
    assert trace_update["metadata"]["transport_reason"] == "short_control_task"
    assert trace_update["metadata"]["capture_full_io"] is False
    assert trace_update["input"]["prompt_hash"] == prompt_hash(
        str(chat.chat_messages("system", secret_prompt)),
    )
    assert trace_update["output"] == {"content_length": len(secret_output), "choice_count": 1}
    assert secret_prompt not in str(trace_update)
    assert secret_output not in str(trace_update)

    completed = [
        event for event in get_run_events(run_id) if event["event_type"] == "llm_call_completed"
    ]
    assert len(completed) == 1
    assert completed[0]["transport_reason"] == "short_control_task"
    assert completed[0]["output_hash"] == prompt_hash(secret_output)
    assert secret_output not in str(completed[0])


@pytest.mark.anyio
async def test_complete_json_chat_redacts_failure_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-transport-failure"
    secret = "sk-live-" + "x" * 40

    async def fake_complete_non_streaming_chat(*_args: Any, **_kwargs: Any) -> ChatResult:
        raise ValueError(f"provider rejected api_key={secret}")

    monkeypatch.setattr(chat, "complete_non_streaming_chat", fake_complete_non_streaming_chat)
    clear_run(run_id)

    with pytest.raises(ValueError, match="provider rejected"):
        await chat.complete_json_chat(
            model="openai/deepseek-test",
            messages=chat.chat_messages("system", "hello"),
            temperature=0.0,
            tags=["agent:reviewer", f"run:{run_id}", "step:10", "task:llm_judge"],
            max_tokens=256,
        )

    failed = [event for event in get_run_events(run_id) if event["event_type"] == "llm_call_failed"]
    assert len(failed) == 1
    assert secret not in str(failed[0])
    assert "[redacted]" in failed[0]["error"]
    assert len(failed[0]["error"]) <= 200


@pytest.mark.anyio
async def test_complete_json_chat_blocks_oversized_prompt_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-prompt-too-large"

    def fail_provider_creation(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("provider client should not be created")

    monkeypatch.setattr(chat, "AsyncOpenAI", fail_provider_creation)
    clear_run(run_id)

    with pytest.raises(PromptGateError, match="prompt_too_large"):
        await chat.complete_json_chat(
            model="openai/deepseek-test",
            messages=chat.chat_messages("system", "x" * (MAX_PROMPT_CHARS + 1)),
            temperature=0.0,
            tags=["agent:researcher", f"run:{run_id}", "step:7", "task:research_synthesis"],
            max_tokens=256,
        )

    failed = [event for event in get_run_events(run_id) if event["event_type"] == "llm_call_failed"]
    started = [
        event for event in get_run_events(run_id) if event["event_type"] == "llm_call_started"
    ]
    assert started == []
    assert len(failed) == 1
    assert failed[0]["error_type"] == "prompt_gate"
    assert "prompt_too_large" in failed[0]["error"]


@pytest.mark.anyio
async def test_complete_json_chat_blocks_secret_prompt_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-secret-prompt"
    secret = "sk-live-" + "x" * 40

    def fail_provider_creation(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("provider client should not be created")

    monkeypatch.setattr(chat, "AsyncOpenAI", fail_provider_creation)
    clear_run(run_id)

    with pytest.raises(PromptGateError, match="secret_like_prompt_content"):
        await chat.complete_json_chat(
            model="openai/deepseek-test",
            messages=chat.chat_messages("system", f"api_key={secret}"),
            temperature=0.0,
            tags=["agent:reviewer", f"run:{run_id}", "step:10", "task:llm_judge"],
            max_tokens=256,
        )

    failed = [event for event in get_run_events(run_id) if event["event_type"] == "llm_call_failed"]
    started = [
        event for event in get_run_events(run_id) if event["event_type"] == "llm_call_started"
    ]
    assert started == []
    assert len(failed) == 1
    assert failed[0]["error_type"] == "prompt_gate"
    assert secret not in str(failed[0])
    assert "secret_like_prompt_content" in failed[0]["error"]


def _payload(
    *,
    agent: str = "planner",
    task: str = "planning",
    message_chars: int = 100,
    max_tokens: int = 1024,
    attempt: int = 1,
    previous_error_type: str | None = None,
    safe_to_stream: bool = True,
) -> TransportPolicyInput:
    return TransportPolicyInput(
        agent=agent,
        task=task,
        message_chars=message_chars,
        max_tokens=max_tokens,
        attempt=attempt,
        previous_error_type=previous_error_type,
        requires_strict_json=True,
        safe_to_stream=safe_to_stream,
    )
