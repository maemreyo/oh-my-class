from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

JudgeRiskLevel = Literal["low", "standard", "high", "rigorous"]

_BORDERLINE_LOW = 6.5
_BORDERLINE_HIGH = 7.5
_SLUG_PATTERN = re.compile(r"[^a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class JudgePolicyContext:
    artifact_type: str
    deterministic_issues: tuple[str, ...] = ()
    subject: str | None = None
    locale: str | None = None
    curriculum: str | None = None
    risk_level: JudgeRiskLevel = "standard"
    borderline_score: float | None = None


@dataclass(frozen=True, slots=True)
class JudgePolicyDecision:
    should_judge: bool
    reasons: tuple[str, ...]


def judge_policy_decision(context: JudgePolicyContext) -> JudgePolicyDecision:
    reasons: list[str] = []
    if context.risk_level in {"high", "rigorous"}:
        reasons.append(f"risk:{context.risk_level}")
    if context.deterministic_issues:
        reasons.append("deterministic_issues")
    if _is_borderline(context.borderline_score):
        reasons.append("borderline_score")
    return JudgePolicyDecision(should_judge=bool(reasons), reasons=tuple(reasons))


def rubric_version_id(context: JudgePolicyContext) -> str:
    parts = ["rubric", _slug(context.artifact_type)]
    _append_optional(parts, "subject", context.subject)
    _append_optional(parts, "locale", context.locale)
    _append_optional(parts, "curriculum", context.curriculum)
    if context.risk_level != "standard":
        parts.extend(("risk", _slug(context.risk_level)))
    parts.extend(_slug(issue) for issue in sorted(set(context.deterministic_issues)))
    return "-".join(parts)


def _append_optional(parts: list[str], key: str, value: str | None) -> None:
    if value is None or value.strip() == "":
        return
    parts.extend((key, _slug(value)))


def _is_borderline(score: float | None) -> bool:
    if score is None:
        return False
    return _BORDERLINE_LOW <= score <= _BORDERLINE_HIGH


def _slug(value: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    if normalized == "":
        return "unspecified"
    return normalized
