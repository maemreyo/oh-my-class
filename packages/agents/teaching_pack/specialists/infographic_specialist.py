from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoInfographicContextError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InfographicScorecard:
    visual_sections: float
    source_grounding: float
    accessible_descriptions: float
    offline_safety: float


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    objectives: list[str] = []
    for item in raw:
        if isinstance(item, str) and (text := item.strip()):
            objectives.append(text)
        elif isinstance(item, dict) and isinstance(item.get("description"), str):
            if text := item["description"].strip():
                objectives.append(text)
    return objectives


def _findings(research_brief: dict[str, Any]) -> list[tuple[str, str]]:
    sources = research_brief.get("sources")
    if not isinstance(sources, list):
        return []
    findings: list[tuple[str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            findings.append((excerpt.strip().split(". ")[0].rstrip(".") + ".", str(source.get("title") or "Approved source")))
    return findings


def build_infographic_sections(lesson_plan: dict[str, Any], research_brief: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    findings = _findings(research_brief)
    sections: list[dict[str, Any]] = [
        {
            "id": f"visual-objective-{index}",
            "title": f"Key idea {index}",
            "content": objective,
            "items": [{"label": "Objective", "value": objective}],
            "components": [{"type": "stat_grid", "stats": [{"label": "Objective", "value": objective}]}],
        }
        for index, objective in enumerate(objectives, start=1)
    ]
    sections.extend({
        "id": f"visual-finding-{index}",
        "title": source_ref,
        "content": finding,
        "items": [{"label": "Source", "value": source_ref}],
        "components": [{"type": "stat_grid", "stats": [{"label": "Source", "value": source_ref}]}],
    } for index, (finding, source_ref) in enumerate(findings, start=1))
    return sections


def score_infographic(sections: list[dict[str, Any]], source_count: int) -> InfographicScorecard:
    return InfographicScorecard(
        visual_sections=1.0 if sections else 0.0,
        source_grounding=1.0 if source_count else 0.0,
        accessible_descriptions=1.0 if all(section.get("content") for section in sections) else 0.0,
        offline_safety=1.0 if not any("http://" in str(section) or "https://" in str(section) for section in sections) else 0.0,
    )


def generate_infographic_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    if not _objectives(lesson_plan):
        raise NoInfographicContextError("no approved learning objectives to build an infographic")
    sections = build_infographic_sections(lesson_plan, research_brief)
    if not sections:
        raise NoInfographicContextError("no approved content to build an infographic")
    scorecard = score_infographic(sections, len(_findings(research_brief)))
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "infographic",
        "theme": theme,
        "title": f"Infographic: {topic}",
        "sections": sections,
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "infographic_scorecard": {
                "visual_sections": scorecard.visual_sections,
                "source_grounding": scorecard.source_grounding,
                "accessible_descriptions": scorecard.accessible_descriptions,
                "offline_safety": scorecard.offline_safety,
            },
        },
        "accessibility": {
            "language": str(lesson_plan.get("locale") or "vi"),
            "alt_texts": [section["content"] for section in sections],
        },
    }
