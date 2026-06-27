from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

TransportMode = Literal["non_streaming", "streaming"]
JsonStrategy = Literal["native_schema", "json_object", "prompt_json", "text_extract"]

LONG_MESSAGE_CHARS = 12_000
LARGE_OUTPUT_TOKENS = 6_000
STREAMING_AGENTS = frozenset({"content_creator"})
SHORT_NON_STREAMING_TASKS = frozenset({"reviewer", "llm_judge", "classification", "schema_rewrite"})
TIMEOUT_ERRORS = frozenset({"timeout", "function_timeout", "function invocation timeout"})


@dataclass(frozen=True, slots=True)
class TransportPolicyInput:
    agent: str
    task: str
    message_chars: int
    max_tokens: int
    attempt: int
    previous_error_type: str | None
    requires_strict_json: bool
    safe_to_stream: bool


@dataclass(frozen=True, slots=True)
class TransportPolicyDecision:
    transport: TransportMode
    reason: str
    json_strategy: JsonStrategy
    capture_full_io: bool


def decide_transport(payload: TransportPolicyInput) -> TransportPolicyDecision:
    if _retry_with_streaming(payload):
        return _decision("streaming", "timeout_retry_streaming", payload)
    if payload.agent in STREAMING_AGENTS:
        return _decision("streaming", "streaming_agent", payload)
    if payload.task in SHORT_NON_STREAMING_TASKS:
        return _decision("non_streaming", "short_control_task", payload)
    if payload.message_chars >= LONG_MESSAGE_CHARS:
        return _decision("streaming", "large_prompt", payload)
    if payload.max_tokens >= LARGE_OUTPUT_TOKENS:
        return _decision("streaming", "large_output", payload)
    return _decision("non_streaming", "default_non_streaming", payload)


def prompt_hash(message_text: str) -> str:
    return sha256(message_text.encode()).hexdigest()


def _retry_with_streaming(payload: TransportPolicyInput) -> bool:
    if payload.previous_error_type is None:
        return False
    return (
        payload.attempt > 1
        and payload.safe_to_stream
        and payload.previous_error_type in TIMEOUT_ERRORS
    )


def _decision(
    transport: TransportMode,
    reason: str,
    payload: TransportPolicyInput,
) -> TransportPolicyDecision:
    return TransportPolicyDecision(
        transport=transport,
        reason=reason,
        json_strategy="text_extract" if payload.requires_strict_json else "prompt_json",
        capture_full_io=False,
    )
