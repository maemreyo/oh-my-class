from __future__ import annotations

from pathlib import Path

import pytest

from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
from packages.agents.tools.capabilities import bind_agent_tools
from packages.agents.tools.fs import (
    ToolUnavailableError,
    clear_write_audit_log,
    read_file,
    write_audit_log,
    write_file,
)


@pytest.mark.asyncio
async def test_agent_runtime_invariant_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    async def fake_complete_json_chat(
        *,
        model: str,
        messages: list[object],
        temperature: float,
        tags: list[str],
    ) -> str:
        captured["model"] = [model]
        captured["message_count"] = [str(len(messages))]
        captured["tags"] = tags
        captured["temperature"] = [str(temperature)]
        return '{"ok": true}'

    from packages.agents import llm

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="researcher",
        run_id="runtime-test-run",
        step=4,
        step_label="post_blueprint_research",
        model="4omc",
    ))

    await runtime.complete_json(
        messages=runtime.messages("system", "user"),
        attempt=1,
        extra_tags=("task:research",),
    )

    assert captured["tags"] == [
        "agent:researcher",
        "step:4",
        "stage:post_blueprint_research",
        "run:runtime-test-run",
        "attempt:2",
        "task:research",
        "pipeline:oh-my-class",
    ]
    assert captured["model"] == ["4omc"]
    assert captured["message_count"] == ["2"]
    assert captured["temperature"] == ["0.3"]


@pytest.mark.asyncio
async def test_agent_runtime_preserves_explicit_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    async def fake_complete_json_chat(
        *,
        model: str,
        messages: list[object],
        temperature: float,
        tags: list[str],
    ) -> str:
        _ = (model, messages)
        captured["temperature"] = [str(temperature)]
        captured["tags"] = tags
        return '{"ok": true}'

    from packages.agents import llm

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="reviewer",
        run_id="runtime-test-run",
        step=7,
        step_label="render_quality",
        model="4omc",
        base_temperature=0.3,
        retry_temperature=0.3,
    ))

    await runtime.complete_json(
        messages=runtime.messages("system", "user"),
        attempt=2,
        extra_tags=("judge:3",),
        temperature=0.5,
    )

    assert captured["temperature"] == ["0.5"]
    assert "attempt:3" in captured["tags"]
    assert "judge:3" in captured["tags"]


@pytest.mark.asyncio
async def test_fs_write_appears_in_audit_log() -> None:
    clear_write_audit_log()
    path = Path(".scratch/issue-026-fs-smoke.txt")

    result = await write_file(str(path), "artifact content", overwrite=True)
    content = await read_file(str(path))
    audit = write_audit_log()

    assert result is True
    assert content == "artifact content"
    assert audit[-1].path == ".scratch/issue-026-fs-smoke.txt"
    assert audit[-1].bytes_written == len("artifact content".encode("utf-8"))


@pytest.mark.asyncio
async def test_fs_rejects_outside_workspace() -> None:
    with pytest.raises(ToolUnavailableError) as exc_info:
        await read_file("/tmp/outside-oh-my-class.txt")

    assert exc_info.value.fail_type == "tool_unavailable"
    assert exc_info.value.tool_name == "fs"


def test_bind_agent_tools_rejects_unimplemented_tool() -> None:
    with pytest.raises(ToolUnavailableError) as exc_info:
        bind_agent_tools("planner", ("task",))

    assert exc_info.value.fail_type == "tool_unavailable"
    assert exc_info.value.tool_name == "task"
