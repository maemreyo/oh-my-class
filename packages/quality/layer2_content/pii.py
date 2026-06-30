from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

PiiCategory = Literal["email", "phone", "url", "social_handle", "student_id", "school_id", "person_name"]


@dataclass(frozen=True, slots=True)
class PiiMatch:
    category: PiiCategory
    token_hash: str


@dataclass(frozen=True, slots=True)
class PiiAuditEvent:
    redaction_counts: dict[PiiCategory, int]
    token_hashes: dict[PiiCategory, tuple[str, ...]]
    low_confidence_hashes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PiiScrubResult:
    value: Any
    audit_event: PiiAuditEvent
    low_confidence_matches: tuple[PiiMatch, ...] = ()


@dataclass(slots=True)
class _ScrubState:
    counters: dict[PiiCategory, int] = field(default_factory=dict)
    token_hashes: dict[PiiCategory, list[str]] = field(default_factory=dict)
    low_confidence_hashes: list[str] = field(default_factory=list)


_HIGH_CONFIDENCE_PATTERNS: tuple[tuple[PiiCategory, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("url", re.compile(r"\bhttps?://[^\s<>)]+", re.IGNORECASE)),
    ("social_handle", re.compile(r"(?<![\w@])@[A-Za-z][A-Za-z0-9_.]{2,30}\b")),
    ("student_id", re.compile(r"\b(?:student|stu|hs|mã học sinh|ma hoc sinh)[\s_-]*(?:id|code|mã|ma)[\s:#-]*[A-Z0-9-]{4,}\b", re.IGNORECASE)),
    ("school_id", re.compile(r"\b(?:school|class|lớp|lop)[\s_-]*(?:id|code|mã|ma)[\s:#-]*[A-Z0-9-]{4,}\b", re.IGNORECASE)),
    ("phone", re.compile(r"(?<!\w)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\w)")),
    ("phone", re.compile(r"(?<!\w)\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")),
    ("person_name", re.compile(r"\b(?:Nguyễn|Nguyen|Trần|Tran|Lê|Le|Phạm|Pham|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Dang|Bùi|Do|Đỗ|Hồ)\s+(?:Văn|Van|Thị|Thi|Minh|Hoàng|Huy|Thu|Ngọc|Bao|Bảo|Anh|Quang)\s+[A-ZÀ-Ỹ][\wÀ-ỹ'-]{1,24}\b", re.IGNORECASE)),
    ("person_name", re.compile(r"\b(?:John|Jane|Mary|Michael|David|Sarah|Emily|Daniel|Peter|Anna|Robert|Linda)\s+(?:Smith|Brown|Johnson|Williams|Jones|Miller|Davis|Wilson|Taylor|Anderson)\b", re.IGNORECASE)),
)

_LOW_CONFIDENCE_NAME = re.compile(r"\b(?:student|learner|pupil|em|bạn)\s+(?:named|called|tên|ten|là|la)\s+([A-ZÀ-Ỹ][\wÀ-ỹ'-]{1,24})\b", re.IGNORECASE)


def scrub_pii(value: Any) -> PiiScrubResult:
    state = _ScrubState()
    scrubbed = _scrub_value(value, state)
    return PiiScrubResult(
        value=scrubbed,
        audit_event=PiiAuditEvent(
            redaction_counts=dict(state.counters),
            token_hashes={category: tuple(hashes) for category, hashes in state.token_hashes.items()},
            low_confidence_hashes=tuple(state.low_confidence_hashes),
        ),
        low_confidence_matches=tuple(PiiMatch(category="person_name", token_hash=token_hash) for token_hash in state.low_confidence_hashes),
    )


def detect_pii(value: Any) -> PiiAuditEvent:
    return scrub_pii(value).audit_event


def _scrub_value(value: Any, state: _ScrubState) -> Any:
    match value:
        case BaseModel():
            return _scrub_value(value.model_dump(), state)
        case str():
            return _scrub_text(value, state)
        case list():
            return [_scrub_value(item, state) for item in value]
        case tuple():
            return tuple(_scrub_value(item, state) for item in value)
        case dict():
            return {key: _scrub_value(item, state) for key, item in value.items()}
        case _:
            return value


def _scrub_text(value: str, state: _ScrubState) -> str:
    text = value
    for category, pattern in _HIGH_CONFIDENCE_PATTERNS:
        text = _replace_pattern(text, category, pattern, state)
    for match in _LOW_CONFIDENCE_NAME.finditer(text):
        state.low_confidence_hashes.append(_hash_token(match.group(1)))
    return text


def _replace_pattern(text: str, category: PiiCategory, pattern: re.Pattern[str], state: _ScrubState) -> str:
    return pattern.sub(lambda match: _replacement(category, match.group(0), state), text)


def _replacement(category: PiiCategory, token: str, state: _ScrubState) -> str:
    count = state.counters.get(category, 0) + 1
    state.counters[category] = count
    state.token_hashes.setdefault(category, []).append(_hash_token(token))
    return f"[REDACTED_{category.upper()}_{count}]"


def _hash_token(token: str) -> str:
    normalized = " ".join(token.casefold().split())
    return hashlib.sha256(f"oh-my-class-pii:{normalized}".encode("utf-8")).hexdigest()
