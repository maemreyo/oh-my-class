from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoDrillObjectivesError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DrillScorecard:
    progression: float
    activity_identity: float
    answer_verifiability: float
    scoped_repairability: float


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        if isinstance(item, str) and (value := item.strip()):
            result.append(value)
        elif isinstance(item, dict) and isinstance(item.get("description"), str):
            if value := item["description"].strip():
                result.append(value)
    return result


def build_drill_activities(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    activities: list[dict[str, Any]] = []
    for index in range(max(5, len(objectives))):
        objective = objectives[index % len(objectives)]
        level = index + 1
        activities.append({
            "type": "question_card",
            "id": f"drill-objective-{index % len(objectives) + 1}-{level}",
            "text": f"Level {level}: Practice this objective: {objective}",
            "options": {
                "A": objective,
                "B": "Use an unrelated skill.",
                "C": "Skip the practice.",
                "D": "Repeat the prompt without responding.",
            },
            "answer": "A",
            "explain": f"Level {level} reinforces the approved objective.",
            "difficulty_level": level,
        })
    return activities


def score_drill(activities: list[dict[str, Any]]) -> DrillScorecard:
    levels = [activity.get("difficulty_level") for activity in activities]
    ids = [str(activity.get("id", "")) for activity in activities]
    return DrillScorecard(
        progression=1.0 if levels == list(range(1, len(activities) + 1)) else 0.0,
        activity_identity=1.0 if len(ids) == len(set(ids)) else 0.0,
        answer_verifiability=1.0 if all(activity.get("answer") in activity.get("options", {}) for activity in activities) else 0.0,
        scoped_repairability=1.0 if all(activity.get("id") for activity in activities) else 0.0,
    )


def generate_drill_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    if not _objectives(lesson_plan):
        raise NoDrillObjectivesError("no approved learning objectives to build a drill")
    activities = build_drill_activities(lesson_plan)
    scorecard = score_drill(activities)
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "drill",
        "theme": theme,
        "title": f"Drill: {topic}",
        "sections": [{"id": "progressive-drill", "title": "Progressive Practice", "components": activities}],
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "drill_scorecard": {
                "progression": scorecard.progression,
                "activity_identity": scorecard.activity_identity,
                "answer_verifiability": scorecard.answer_verifiability,
                "scoped_repairability": scorecard.scoped_repairability,
            },
            "grounding_source_count": len(research_brief.get("sources", [])) if isinstance(research_brief.get("sources"), list) else 0,
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
