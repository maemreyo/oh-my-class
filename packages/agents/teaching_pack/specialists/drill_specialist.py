from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from common.contracts.grade_band import grade_band_for_label
from packages.agents.teaching_pack.subject_packs.math_question_builder import (
    build_math_questions,
    to_question_card,
)


class NoDrillObjectivesError(ValueError):
    pass


def _is_math_subject(lesson_plan: dict[str, Any]) -> bool:
    return str(lesson_plan.get("subject") or "").strip().lower() == "math"


def _deterministic_seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(digest[:8], 16)


def _build_math_drill_activities(lesson_plan: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Real, solver-verified progressive math practice (#447); falls back to
    the generic objective-repetition builder (returns None) when no Grade
    Band can be determined from the lesson plan."""
    grade_level = str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or "")
    grade_band = grade_band_for_label(grade_level)
    if grade_band is None:
        return None
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "lesson")
    locale = str(lesson_plan.get("locale") or "vi")
    seed = _deterministic_seed(topic, grade_band.value, "drill")
    questions = build_math_questions(grade_band, count=5, seed=seed)
    activities: list[dict[str, Any]] = []
    for level, question in enumerate(questions, start=1):
        card = to_question_card(question, locale=locale)
        card["id"] = f"{card['id']}-drill-{level}"
        card["difficulty_level"] = level
        activities.append(card)
    return activities


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
    math_activities = _build_math_drill_activities(lesson_plan) if _is_math_subject(lesson_plan) else None
    activities = math_activities if math_activities is not None else build_drill_activities(lesson_plan)
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
