from __future__ import annotations

import re
from typing import Final

MAX_ERROR_SUMMARY_CHARS: Final = 200
_REDACTED: Final = "[redacted]"
_BEARER_TOKEN_PATTERN: Final = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_API_KEY_PATTERN: Final = re.compile(
    r"(?i)(api[_-]?key|authorization|token|secret|password)\s*[:=]\s*[^\s,;]+",
)
_LONG_SECRET_PATTERN: Final = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")


def safe_error_summary(error: BaseException, *, limit: int = MAX_ERROR_SUMMARY_CHARS) -> str:
    raw_summary = f"{type(error).__name__}: {error}"
    return _truncate(_redact(raw_summary), limit)


def safe_message_summary(message: str, *, limit: int = MAX_ERROR_SUMMARY_CHARS) -> str:
    return _truncate(_redact(message), limit)


def _redact(text: str) -> str:
    without_bearer = _BEARER_TOKEN_PATTERN.sub(f"Bearer {_REDACTED}", text)
    without_keys = _API_KEY_PATTERN.sub(
        lambda match: f"{match.group(1)}={_REDACTED}",
        without_bearer,
    )
    return _LONG_SECRET_PATTERN.sub(_REDACTED, without_keys)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]
