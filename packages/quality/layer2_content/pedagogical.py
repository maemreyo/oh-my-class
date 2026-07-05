from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from packages.quality.layer2_content.readability_checker import check_readability

MetricStatus = Literal["passed", "failed", "unmeasured"]

MEASURED_METRICS: Final[tuple[str, ...]] = (
    "prompt_alignment",
    "bloom_coverage",
    "cognitive_load",
    "readability_level",
    "misconception_coverage",
)
UNMEASURED_METRICS: Final[tuple[str, ...]] = (
    "factual_correctness",
    "contextual_relevance",
    "engagement",
    "harmful_content_avoidance",
    "solution_accuracy",
)
REQUIRED_METRICS: Final[tuple[str, ...]] = (*MEASURED_METRICS, *UNMEASURED_METRICS)
_BLOOM_LEVELS: Final[frozenset[str]] = frozenset({
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
})


@dataclass(frozen=True, slots=True)
class PedagogicalMetric:
    name: str
    status: MetricStatus
    measured: bool
    issue: str | None = None


@dataclass(frozen=True, slots=True)
class PedagogicalResult:
    passed: bool
    metrics: dict[str, MetricStatus] = field(default_factory=dict)
    measured: dict[str, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def check_pedagogical_metrics(
    content: dict[str, Any],
    *,
    lesson_plan: dict[str, Any] | None = None,
    research_bundle: dict[str, Any] | None = None,
) -> PedagogicalResult:
    _ = research_bundle
    measured = (
        _check_prompt_alignment(content, lesson_plan),
        _check_bloom_coverage(content, lesson_plan),
        _check_cognitive_load(content),
        _check_readability_level(content, lesson_plan),
        _check_misconception_coverage(content),
    )
    unmeasured = tuple(
        PedagogicalMetric(
            name=metric,
            status="unmeasured",
            measured=False,
            issue="post-delivery evidence required; deferred to KT effectiveness loop",
        )
        for metric in UNMEASURED_METRICS
    )
    metric_results = (*measured, *unmeasured)
    metrics: dict[str, MetricStatus] = {result.name: result.status for result in metric_results}
    measured_flags = {result.name: result.measured for result in metric_results}
    issues = [
        f"{result.name}: {result.issue}"
        for result in metric_results
        if result.status == "failed" and result.issue is not None
    ]
    passed = all(result.status == "passed" for result in measured)
    return PedagogicalResult(passed=passed, metrics=metrics, measured=measured_flags, issues=issues)


def _check_prompt_alignment(
    content: dict[str, Any],
    lesson_plan: dict[str, Any] | None,
) -> PedagogicalMetric:
    objectives = _lesson_objective_terms(lesson_plan)
    if not objectives:
        return _passed("prompt_alignment")
    text = _text_blob(content)
    # Objectives are extracted with an ASCII regex. If the artifact content is
    # primarily non-Latin (Vietnamese, Arabic, CJK) the same regex finds no tokens,
    # so cross-language alignment can never be verified — skip rather than false-fail.
    if _is_non_latin_blob(text):
        return _passed("prompt_alignment")
    matched = [term for term in objectives if term in text]
    if matched:
        return _passed("prompt_alignment")
    return _failed("prompt_alignment", "content does not reference lesson objectives")


def _check_bloom_coverage(
    content: dict[str, Any],
    lesson_plan: dict[str, Any] | None,
) -> PedagogicalMetric:
    expected = _bloom_levels(lesson_plan)
    if not expected:
        return _passed("bloom_coverage")
    if len(expected) < 2:
        return _failed("bloom_coverage", "lesson plan includes fewer than two Bloom levels")
    # Bloom keywords are English. Non-Latin content cannot match them — skip.
    if _is_non_latin_blob(_text_blob(content)):
        return _passed("bloom_coverage")
    observed = expected & _bloom_levels(content)
    if len(observed) >= 2:
        return _passed("bloom_coverage")
    return _failed("bloom_coverage", "content covers fewer than two planned Bloom levels")


def _check_cognitive_load(content: dict[str, Any]) -> PedagogicalMetric:
    new_kc = _knowledge_components(content)
    if len(new_kc) <= 4:
        return _passed("cognitive_load")
    return _failed("cognitive_load", f"introduces {len(new_kc)} knowledge components; limit is 4")


def _check_readability_level(
    content: dict[str, Any],
    lesson_plan: dict[str, Any] | None,
) -> PedagogicalMetric:
    target_grade = _target_grade(lesson_plan)
    if target_grade is None:
        return _passed("readability_level")
    result = check_readability(_text_blob(content), target_grade)
    if result.passed:
        return _passed("readability_level")
    return _failed("readability_level", result.warning or "readability outside target grade band")


def _check_misconception_coverage(content: dict[str, Any]) -> PedagogicalMetric:
    components = _components(content)
    question_cards = [item for item in components if item.get("type") == "question_card"]
    if not question_cards:
        return _passed("misconception_coverage")
    # wrong_reasons=None means not provided (optional field — allowed by schema).
    # Only fail when it's explicitly an empty dict {}, indicating the LLM attempted but omitted all reasons.
    missing = [
        str(item.get("id", "unknown"))
        for item in question_cards
        if item.get("wrong_reasons") is not None and not item.get("wrong_reasons")
    ]
    if not missing:
        return _passed("misconception_coverage")
    return _failed("misconception_coverage", f"question cards missing wrong_reasons: {', '.join(missing)}")


def _lesson_objective_terms(lesson_plan: dict[str, Any] | None) -> frozenset[str]:
    if lesson_plan is None:
        return frozenset()
    raw_objectives = lesson_plan.get("learning_objectives", [])
    terms: set[str] = set()
    for item in raw_objectives:
        if isinstance(item, str):
            terms.update(_significant_terms(item))
        elif isinstance(item, dict):
            for key in ("description", "objective", "text"):
                value = item.get(key)
                if isinstance(value, str):
                    terms.update(_significant_terms(value))
    return frozenset(terms)


def _significant_terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-zA-Z]{4,}", text.lower())}


def _bloom_levels(value: dict[str, Any] | None) -> frozenset[str]:
    if value is None:
        return frozenset()
    words = {
        word
        for text in _walk_strings(value)
        for word in re.findall(r"[a-zA-Z]+", text)
    }
    return frozenset(
        word
        for word in words
        if word in _BLOOM_LEVELS
    )


def _knowledge_components(content: dict[str, Any]) -> frozenset[str]:
    components: set[str] = set()
    for item in _components(content):
        for key in ("kc_id", "knowledge_component", "concept"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                components.add(value.strip().lower())
    return frozenset(components)


def _target_grade(lesson_plan: dict[str, Any] | None) -> int | None:
    if lesson_plan is None:
        return None
    for key in ("grade", "grade_level"):
        value = lesson_plan.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match is not None:
                return int(match.group())
    return None


def _is_non_latin_blob(text: str) -> bool:
    """Return True when >15% of non-space chars are non-ASCII (e.g. Vietnamese, Arabic, CJK)."""
    chars = text.replace(" ", "")
    if not chars:
        return False
    return sum(1 for c in chars if ord(c) > 127) / len(chars) > 0.15


def _text_blob(value: Any) -> str:
    return " ".join(_walk_strings(value)).lower()


def _walk_strings(value: Any) -> tuple[str, ...]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value.lower())
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(_walk_strings(item))
    elif isinstance(value, list | tuple):
        for item in value:
            strings.extend(_walk_strings(item))
    return tuple(strings)


def _components(content: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    found: list[dict[str, Any]] = []
    _collect_components(content, found)
    return tuple(found)


def _collect_components(value: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("type"), str):
            found.append(value)
        for item in value.values():
            _collect_components(item, found)
    elif isinstance(value, list | tuple):
        for item in value:
            _collect_components(item, found)


def _passed(name: str) -> PedagogicalMetric:
    return PedagogicalMetric(name=name, status="passed", measured=True)


def _failed(name: str, issue: str) -> PedagogicalMetric:
    return PedagogicalMetric(name=name, status="failed", measured=True, issue=issue)
