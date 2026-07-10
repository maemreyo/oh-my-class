from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from common.contracts.grade_band import grade_band_for_label
from packages.agents.teaching_pack.subject_packs.math_question_builder import (
    build_math_questions,
    to_question_card,
)


class NoQuizObjectivesError(ValueError):
    pass


def _is_math_subject(lesson_plan: dict[str, Any]) -> bool:
    return str(lesson_plan.get("subject") or "").strip().lower() == "math"


def _deterministic_seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(digest[:8], 16)


def _build_math_quiz_questions(lesson_plan: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Real, solver-verified math questions (#447) when a Grade Band can be
    determined; falls back to the generic objective-matching builder
    (returns None) otherwise -- never silently mislabels an unparseable
    grade as a specific band's content."""
    grade_level = str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or "")
    grade_band = grade_band_for_label(grade_level)
    if grade_band is None:
        return None
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "lesson")
    locale = str(lesson_plan.get("locale") or "vi")
    seed = _deterministic_seed(topic, grade_band.value)
    questions = build_math_questions(grade_band, count=8, seed=seed)
    return [to_question_card(question, locale=locale) for question in questions]


@dataclass(frozen=True, slots=True)
class QuizScorecard:
    objective_coverage: float
    question_identity: float
    assessment_alignment: float
    answer_verifiability: float


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
    raw_objectives = lesson_plan.get("learning_objectives")
    if not isinstance(raw_objectives, list):
        return []
    objectives: list[str] = []
    for objective in raw_objectives:
        if isinstance(objective, str) and (text := objective.strip()):
            objectives.append(text)
        elif isinstance(objective, dict) and isinstance(objective.get("description"), str):
            if text := objective["description"].strip():
                objectives.append(text)
    return objectives


def build_quiz_questions(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        return []
    questions: list[dict[str, Any]] = []
    for index in range(max(8, len(objectives))):
        objective = objectives[index % len(objectives)]
        questions.append({
            "type": "question_card",
            "id": f"quiz-objective-{index % len(objectives) + 1}-{index + 1}",
            "text": f"Which statement best matches this learning objective? {objective}",
            "options": {
                "A": objective,
                "B": "A different lesson objective.",
                "C": "An unrelated classroom task.",
                "D": "No response is needed.",
            },
            "answer": "A",
            "explain": "The correct choice matches the approved learning objective.",
        })
    return questions


def score_quiz(questions: list[dict[str, Any]], objective_count: int) -> QuizScorecard:
    question_ids = [str(question.get("id", "")) for question in questions]
    return QuizScorecard(
        objective_coverage=round(min(len(questions), objective_count) / objective_count, 3) if objective_count else 0.0,
        question_identity=1.0 if len(question_ids) == len(set(question_ids)) else 0.0,
        assessment_alignment=1.0 if all(question.get("text") for question in questions) else 0.0,
        answer_verifiability=1.0 if all(question.get("answer") in question.get("options", {}) for question in questions) else 0.0,
    )


def generate_quiz_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise NoQuizObjectivesError("no approved learning objectives to build a quiz")
    math_questions = _build_math_quiz_questions(lesson_plan) if _is_math_subject(lesson_plan) else None
    questions = math_questions if math_questions is not None else build_quiz_questions(lesson_plan)
    scorecard = score_quiz(questions, len(objectives))
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "quiz",
        "theme": theme,
        "title": f"Quiz: {topic}",
        "sections": [{"id": "quiz-questions", "title": "Questions", "components": questions}],
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "quiz_scorecard": {
                "objective_coverage": scorecard.objective_coverage,
                "question_identity": scorecard.question_identity,
                "assessment_alignment": scorecard.assessment_alignment,
                "answer_verifiability": scorecard.answer_verifiability,
            },
            "grounding_source_count": len(research_brief.get("sources", [])) if isinstance(research_brief.get("sources"), list) else 0,
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
