from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoRoadmapObjectivesError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RoadmapScorecard:
    milestone_count: float
    objective_coverage: float
    dependency_order: float
    scoped_editability: float


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


def build_roadmap_sections(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    sections: list[dict[str, Any]] = []
    for index, objective in enumerate(objectives, start=1):
        sections.append({
            "id": f"milestone-{index}",
            "title": f"Milestone {index}",
            "subtitle": objective,
            "tag_num": str(index),
            "components": [{"type": "paragraph", "text": objective}],
        })
    return sections


def score_roadmap(sections: list[dict[str, Any]], objective_count: int) -> RoadmapScorecard:
    identifiers = [str(section.get("id", "")) for section in sections]
    return RoadmapScorecard(
        milestone_count=1.0 if sections else 0.0,
        objective_coverage=round(len(sections) / objective_count, 3) if objective_count else 0.0,
        dependency_order=1.0 if identifiers == [f"milestone-{index}" for index in range(1, len(sections) + 1)] else 0.0,
        scoped_editability=1.0 if len(identifiers) == len(set(identifiers)) else 0.0,
    )


def generate_roadmap_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise NoRoadmapObjectivesError("no approved learning objectives to build a roadmap")
    sections = build_roadmap_sections(lesson_plan)
    scorecard = score_roadmap(sections, len(objectives))
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    subject = str(lesson_plan.get("subject") or "General")
    return {
        "artifact_type": "roadmap",
        "theme": theme,
        "title": f"Roadmap: {topic}",
        "sections": sections,
        "metadata": {
            "hero": {
                "eyebrow": subject,
                "title": f"Roadmap: {topic}",
                "lede": "A milestone sequence derived from the approved learning objectives.",
                "stats": [{"label": "Milestones", "value": str(len(sections)), "variant": "target"}],
            },
            "sidebar": {
                "title": topic,
                "subtitle": subject,
                "nav": [{"label": section["title"], "href": f"#{section['id']}"} for section in sections],
            },
            "roadmap_scorecard": {
                "milestone_count": scorecard.milestone_count,
                "objective_coverage": scorecard.objective_coverage,
                "dependency_order": scorecard.dependency_order,
                "scoped_editability": scorecard.scoped_editability,
            },
            "grounding_source_count": len(research_brief.get("sources", [])) if isinstance(research_brief.get("sources"), list) else 0,
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
