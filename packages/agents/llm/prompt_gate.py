from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from packages.agents.llm.error_summary import safe_message_summary

MAX_PROMPT_CHARS: Final = 120_000
_SECRET_PATTERN: Final = re.compile(
    r"(?i)(Bearer\s+[A-Za-z0-9._~+/=-]{16,}|"
    r"(?:api[_-]?key|authorization|token|secret|password)\s*[:=]\s*[^\s,;]{8,}|"
    r"\b(?:sk|pk|rk|xoxb|ghp|github_pat)-[A-Za-z0-9_-]{20,}\b)",
)


@dataclass(frozen=True, slots=True)
class PromptGateError(ValueError):
    reason: str
    message_chars: int

    def __str__(self) -> str:
        return f"pre_llm_prompt_gate_blocked: {self.reason} message_chars={self.message_chars}"


def enforce_prompt_gate(prompt_text: str, message_chars: int) -> None:
    if message_chars > MAX_PROMPT_CHARS:
        raise PromptGateError("prompt_too_large", message_chars)
    if _SECRET_PATTERN.search(prompt_text) is not None:
        raise PromptGateError("secret_like_prompt_content", message_chars)


def safe_prompt_gate_detail(error: PromptGateError) -> str:
    return safe_message_summary(str(error))
