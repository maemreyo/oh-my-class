from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from packages.agents.config.models import MAX_TOKENS
from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.llm.prompt_gate import PromptGateError, enforce_prompt_gate
from packages.agents.llm.transport_policy import (
    TransportPolicyDecision,
    TransportPolicyInput,
    decide_transport,
    prompt_hash,
)

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

_AGENT_MAX_TOKENS: dict[str, int] = {
    "planner": MAX_TOKENS.planner,
    "researcher": MAX_TOKENS.researcher,
    "content_creator": MAX_TOKENS.content_creator,
    "diagnostician": MAX_TOKENS.diagnostician,
    "reviewer": MAX_TOKENS.reviewer,
}
_DEFAULT_MAX_TOKENS = MAX_TOKENS.default


@dataclass(frozen=True, slots=True)
class TransportResult:
    content: str
    usage: dict[str, object] | None
    choice_count: int
    response_id: str
    response_model: str


@dataclass(frozen=True, slots=True)
class ParsedTags:
    run_id: str
    agent_name: str
    attempt: int
    step: int
    task_name: str
    previous_error_type: str | None

    @classmethod
    def from_tags(cls, tags: list[str]) -> ParsedTags:
        values = {tag.split(":", 1)[0]: tag.split(":", 1)[1] for tag in tags if ":" in tag}
        agent = values.get("agent", "")
        return cls(
            run_id=values.get("run", ""),
            agent_name=agent,
            attempt=int(values.get("attempt", "1")),
            step=int(values.get("step", "0")),
            task_name=values.get("task", agent),
            previous_error_type=values.get("previous_error"),
        )


@dataclass(frozen=True, slots=True)
class CallContext:
    request_model: str
    run_id: str
    agent_name: str
    step: int
    attempt: int
    max_tokens: int
    message_chars: int
    decision: TransportPolicyDecision
    started: float

    @property
    def started_event(self) -> dict[str, object]:
        return {
            "agent": self.agent_name,
            "model": self.request_model,
            "attempt": self.attempt,
            "max_tokens": self.max_tokens,
            "message_chars": self.message_chars,
            "transport": self.decision.transport,
            "transport_reason": self.decision.reason,
        }

    def trace_input(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
    ) -> dict[str, object]:
        return {
            "messages": len(messages),
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "message_chars": self.message_chars,
            "prompt_hash": prompt_hash(str(messages)),
        }

    def trace_metadata(self, result: TransportResult) -> dict[str, object]:
        return {
            "attempt": self.attempt,
            "response_id": result.response_id,
            "response_model": result.response_model,
            "stream": self.decision.transport == "streaming",
            "transport_reason": self.decision.reason,
            "json_strategy": self.decision.json_strategy,
            "capture_full_io": self.decision.capture_full_io,
        }

    def completed_event(self, result: TransportResult) -> dict[str, object]:
        return {
            "agent": self.agent_name,
            "model": self.request_model,
            "attempt": self.attempt,
            "step": self.step,
            "duration_s": round(time.monotonic() - self.started, 1),
            "response_chars": len(result.content),
            "transport": self.decision.transport,
            "transport_reason": self.decision.reason,
            "output_hash": prompt_hash(result.content),
            "usage": result.usage,
        }

    def failed_event(self, exc: Exception) -> dict[str, object]:
        return {
            "agent": self.agent_name,
            "model": self.request_model,
            "attempt": self.attempt,
            "step": self.step,
            "duration_s": round(time.monotonic() - self.started, 1),
            "error": safe_error_summary(exc),
            "error_type": error_type(exc),
        }

    def enforce_prompt_gate(self, messages: list[ChatCompletionMessageParam]) -> None:
        enforce_prompt_gate(str(messages), self.message_chars)


def build_call_context(
    model: str,
    messages: list[ChatCompletionMessageParam],
    tags: list[str],
    max_tokens: int | None,
) -> CallContext:
    parsed = ParsedTags.from_tags(tags)
    resolved_max_tokens = max_tokens or _AGENT_MAX_TOKENS.get(
        parsed.agent_name,
        _DEFAULT_MAX_TOKENS,
    )
    message_chars = message_chars_for(messages)
    decision = decide_transport(TransportPolicyInput(
        agent=parsed.agent_name,
        task=parsed.task_name,
        message_chars=message_chars,
        max_tokens=resolved_max_tokens,
        attempt=parsed.attempt,
        previous_error_type=parsed.previous_error_type,
        requires_strict_json=True,
        safe_to_stream=True,
    ))
    return CallContext(
        request_model=model.removeprefix("openai/"),
        run_id=parsed.run_id,
        agent_name=parsed.agent_name,
        step=parsed.step,
        attempt=parsed.attempt,
        max_tokens=resolved_max_tokens,
        message_chars=message_chars,
        decision=decision,
        started=time.monotonic(),
    )


def message_chars_for(messages: list[ChatCompletionMessageParam]) -> int:
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            total += len(str(content))
    return total


def error_type(exc: Exception) -> str:
    if isinstance(exc, PromptGateError):
        return "prompt_gate"
    text = str(exc).lower()
    if "timeout" in text:
        return "timeout"
    if "json" in text:
        return "json_parse"
    if "empty" in text:
        return "empty_response"
    return type(exc).__name__.lower()
