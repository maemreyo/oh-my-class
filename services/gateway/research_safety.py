from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final, assert_never

if TYPE_CHECKING:
    from common.contracts.run_contract import JsonValue

PII_KEYS: Final = frozenset({"name", "student_name", "email", "score", "class_id", "student_id"})
_EMAIL_PATTERN: Final = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_STUDENT_NAME_PATTERN: Final = re.compile(
    r"\b(student|pupil)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
)


def evidence_terms(evidence: dict[str, JsonValue] | None) -> str:
    if evidence is None:
        return ""
    terms: list[str] = []
    for key, value in evidence.items():
        if key in PII_KEYS:
            continue
        terms.extend(_json_terms(value))
    return scrub_text(" ".join(terms))


def scrub_text(value: str) -> str:
    without_email = _EMAIL_PATTERN.sub("", value)
    without_student_names = _STUDENT_NAME_PATTERN.sub(r"\1", without_email)
    return " ".join(without_student_names.split())


def minimize_class_info(class_info: dict[str, JsonValue]) -> dict[str, JsonValue]:
    minimized = dict(class_info)
    evidence = minimized.get("student_evidence")
    if isinstance(evidence, dict):
        minimized["student_evidence"] = minimize_student_evidence(evidence)
    return minimized


def minimize_student_evidence(evidence: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: value for key, value in evidence.items() if key not in PII_KEYS}


def _json_terms(value: JsonValue) -> tuple[str, ...]:
    match value:
        case str():
            return (value,)
        case int() | float() | bool() | None:
            return ()
        case list():
            return tuple(term for item in value for term in _json_terms(item))
        case dict():
            return tuple(
                term
                for key, item in value.items()
                if key not in PII_KEYS
                for term in _json_terms(item)
            )
        case unreachable:
            assert_never(unreachable)
