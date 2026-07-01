from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from packages.llm_client.errors import BadPromptError, PermanentProviderError


_UNSAFE_PATTERN = re.compile(r"\b(?:weapon|self-harm|suicide|pornographic)\b", re.IGNORECASE)
_PII_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"\b(?:student|pupil)\s+(?:name|email|phone)\b",
    re.IGNORECASE,
)
_VIETNAMESE_MARKERS = frozenset("ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


@dataclass(frozen=True, slots=True)
class MiddlewareCallContext:
    agent: str
    task: str
    run_id: str | None
    step: int | None
    locale: str | None = None
    expects_json: bool = False


@dataclass(frozen=True, slots=True)
class MiddlewareMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class MiddlewareResult:
    content: str
    flags: tuple[str, ...] = field(default_factory=tuple)


class CallMiddlewareRunner:
    def before_call(
        self,
        messages: list[MiddlewareMessage],
        context: MiddlewareCallContext,
    ) -> list[MiddlewareMessage]:
        _check_cost_tags(context)
        coalesced = _coalesce_system_messages(messages)
        for message in coalesced:
            if _UNSAFE_PATTERN.search(message.content):
                raise BadPromptError("content_safety_input_blocked")
        return coalesced

    def after_call(self, content: str, context: MiddlewareCallContext) -> MiddlewareResult:
        flags: list[str] = []
        if _UNSAFE_PATTERN.search(content):
            raise PermanentProviderError("content_safety_output_blocked")
        scrubbed = _PII_PATTERN.sub("[redacted-pii]", content)
        if scrubbed != content:
            flags.append("pii_output_scrubbed")
        if context.expects_json:
            scrubbed = _repair_json_payload(scrubbed)
            if scrubbed != content:
                flags.append("structured_output_repaired")
        if context.locale == "vi" and not _contains_vietnamese_marker(scrubbed):
            flags.append("locale_vi_unconfirmed")
        return MiddlewareResult(content=scrubbed, flags=tuple(flags))


def _check_cost_tags(context: MiddlewareCallContext) -> None:
    if context.agent == "unknown" or context.task == "unknown":
        raise BadPromptError("missing_cost_tag_context")


def _coalesce_system_messages(messages: list[MiddlewareMessage]) -> list[MiddlewareMessage]:
    system_messages = [message.content for message in messages if message.role == "system"]
    if len(system_messages) <= 1:
        return messages
    coalesced = MiddlewareMessage(role="system", content="\n\n".join(system_messages))
    non_system = [message for message in messages if message.role != "system"]
    return [coalesced, *non_system]


def _require_json(content: str) -> None:
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise BadPromptError("structured_output_invalid_json") from exc


def _repair_json_payload(content: str) -> str:
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        candidate = _extract_json_candidate(content)
    _require_json(candidate)
    return candidate


def _extract_json_candidate(content: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(?P<body>.*?)```", content, re.DOTALL | re.IGNORECASE)
    if fenced is not None:
        return fenced.group("body").strip()
    object_start = content.find("{")
    object_end = content.rfind("}")
    if object_start != -1 and object_end > object_start:
        return content[object_start: object_end + 1]
    array_start = content.find("[")
    array_end = content.rfind("]")
    if array_start != -1 and array_end > array_start:
        return content[array_start: array_end + 1]
    return content


def _contains_vietnamese_marker(content: str) -> bool:
    return any(character.lower() in _VIETNAMESE_MARKERS for character in content)


def expects_json_from_response_format(response_format: object) -> bool:
    match response_format:
        case {"type": "json_object"}:
            return True
        case _:
            return False
