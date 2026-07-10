from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoPracticeObjectivesError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorksheetScorecard:
    scaffolding: float
    progression: float
    retrieval: float
    feedback: float
    objective_coverage: float


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


def build_worksheet_questions(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        return []
    questions: list[dict[str, Any]] = []
    for index in range(max(3, len(objectives))):
        objective = objectives[index % len(objectives)]
        questions.append({
            "type": "question_card",
            "id": f"worksheet-objective-{index % len(objectives) + 1}-{index + 1}",
            "text": f"Use this lesson objective in your own words: {objective}",
            "options": {"A": "Write your response.", "B": "", "C": "", "D": ""},
            "answer": objective,
            "explain": "Teacher reference only; student rendering omits this field.",
        })
    return questions


def score_worksheet(questions: list[dict[str, Any]], objective_count: int) -> WorksheetScorecard:
    question_count = len(questions)
    coverage = round(min(question_count, objective_count) / objective_count, 3) if objective_count else 0.0
    return WorksheetScorecard(
        scaffolding=1.0 if question_count >= 3 else 0.0,
        progression=1.0 if question_count >= objective_count else round(question_count / objective_count, 3),
        retrieval=1.0 if all(question.get("text") for question in questions) else 0.0,
        feedback=1.0 if all(question.get("explain") for question in questions) else 0.0,
        objective_coverage=coverage,
    )


def generate_worksheet_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise NoPracticeObjectivesError("no approved learning objectives to build worksheet practice")
    questions = build_worksheet_questions(lesson_plan)
    scorecard = score_worksheet(questions, len(objectives))
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    sources = research_brief.get("sources")
    traces = [
        {"question_id": question["id"], "objective_ref": f"objective-{index % len(objectives) + 1}"}
        for index, question in enumerate(questions)
    ]
    return {
        "artifact_type": "worksheet",
        "theme": theme,
        "title": f"Worksheet: {topic}",
        "sections": [{
            "id": "guided-practice",
            "title": "Guided Practice",
            "instructions": "Respond to each prompt using the lesson evidence.",
            "components": questions,
        }],
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "worksheet_question_traces": traces,
            "grounding_source_count": len(sources) if isinstance(sources, list) else 0,
            "worksheet_scorecard": {
                "scaffolding": scorecard.scaffolding,
                "progression": scorecard.progression,
                "retrieval": scorecard.retrieval,
                "feedback": scorecard.feedback,
                "objective_coverage": scorecard.objective_coverage,
            },
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
