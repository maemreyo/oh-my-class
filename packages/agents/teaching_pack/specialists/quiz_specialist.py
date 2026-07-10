from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoQuizObjectivesError(ValueError):
    pass


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
    questions = build_quiz_questions(lesson_plan)
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
