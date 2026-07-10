from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoExitTicketObjectivesError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExitTicketScorecard:
    brevity: float
    objective_sampling: float
    scoring: float
    identity_stability: float


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


def build_exit_ticket_questions(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    questions: list[dict[str, Any]] = []
    for index in range(3):
        objective = objectives[index % len(objectives)]
        questions.append({
            "type": "question_card",
            "id": f"exit-ticket-objective-{index % len(objectives) + 1}-{index + 1}",
            "text": f"Briefly demonstrate: {objective}",
            "options": {
                "A": objective,
                "B": "An unrelated outcome.",
                "C": "Skip the response.",
                "D": "Repeat the prompt.",
            },
            "answer": "A",
            "explain": "The answer samples the approved learning objective.",
        })
    return questions


def score_exit_ticket(questions: list[dict[str, Any]], objective_count: int) -> ExitTicketScorecard:
    question_ids = [str(question.get("id", "")) for question in questions]
    return ExitTicketScorecard(
        brevity=1.0 if len(questions) == 3 else 0.0,
        objective_sampling=round(min(len(questions), objective_count) / objective_count, 3) if objective_count else 0.0,
        scoring=1.0 if all(question.get("answer") in question.get("options", {}) for question in questions) else 0.0,
        identity_stability=1.0 if len(question_ids) == len(set(question_ids)) else 0.0,
    )


def generate_exit_ticket_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise NoExitTicketObjectivesError("no approved learning objectives to build an exit ticket")
    questions = build_exit_ticket_questions(lesson_plan)
    scorecard = score_exit_ticket(questions, len(objectives))
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "exit_ticket",
        "theme": theme,
        "title": f"Exit Ticket: {topic}",
        "sections": [{"id": "exit-ticket", "title": "Quick Check", "components": questions}],
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "exit_ticket_scorecard": {
                "brevity": scorecard.brevity,
                "objective_sampling": scorecard.objective_sampling,
                "scoring": scorecard.scoring,
                "identity_stability": scorecard.identity_stability,
            },
            "grounding_source_count": len(research_brief.get("sources", [])) if isinstance(research_brief.get("sources"), list) else 0,
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
