from __future__ import annotations

from typing import Any


def summarize_lesson_plan(lesson_plan: dict[str, Any]) -> dict[str, Any]:
    learning_plan = lesson_plan.get("learning_plan")
    return {
        "topic": lesson_plan.get("topic"),
        "grade_level": lesson_plan.get("grade_level"),
        "subject": lesson_plan.get("subject"),
        "duration_minutes": lesson_plan.get("duration_minutes"),
        "learning_objectives": _summarize_objectives(lesson_plan.get("learning_objectives")),
        "methodology_tags": _methodology_tags(lesson_plan.get("methodology")),
        "lesson_flow": _summarize_learning_plan(learning_plan),
        "assessment_checkpoints": _summarize_assessments(
            lesson_plan.get("assessment_checkpoints")
        ),
    }


def summarize_research_bundle(research_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "topic": research_bundle.get("topic"),
        "key_findings": _truncate_list(research_bundle.get("key_findings"), limit=3),
        "verified_sources": _verified_sources(research_bundle.get("sources")),
    }


def _summarize_objectives(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    objectives: list[dict[str, Any]] = []
    for item in value[:6]:
        if isinstance(item, dict):
            objectives.append({
                "description": _truncate_text(item.get("description"), max_chars=180),
                "bloom_level": item.get("bloom_level"),
            })
    return objectives


def _methodology_tags(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    tags = value.get("tags")
    if not isinstance(tags, list):
        return []
    return [str(tag) for tag in tags[:6]]


def _summarize_learning_plan(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    phases: list[dict[str, Any]] = []
    for event, phase in list(value.items())[:9]:
        if isinstance(phase, dict):
            phases.append({
                "event": event,
                "title": phase.get("title") or phase.get("name"),
                "duration_minutes": phase.get("duration_minutes"),
                "activity_summary": _activity_summary(phase.get("activities")),
            })
        else:
            phases.append({"event": event, "title": _truncate_text(phase, max_chars=120)})
    return phases


def _summarize_assessments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    assessments: list[dict[str, Any]] = []
    for item in value[:4]:
        if isinstance(item, dict):
            assessments.append({
                "type": item.get("type"),
                "description": _truncate_text(item.get("description"), max_chars=160),
                "trigger": _truncate_text(item.get("trigger"), max_chars=80),
            })
    return assessments


def _verified_sources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sources: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("verification_status") != "VERIFIED":
            continue
        sources.append({
            "title": _truncate_text(item.get("title"), max_chars=120),
            "verification_status": item.get("verification_status"),
        })
        if len(sources) == 5:
            break
    return sources


def _truncate_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value[:limit] if (text := _truncate_text(item, max_chars=220))]


def _activity_summary(value: Any) -> str | None:
    if isinstance(value, list):
        return _truncate_text(" ".join(str(item) for item in value[:2]), max_chars=180)
    return _truncate_text(value, max_chars=180)


def _truncate_text(value: Any, *, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
