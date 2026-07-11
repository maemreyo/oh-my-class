from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from common.contracts.grade_band import grade_band_for_label
from packages.agents.teaching_pack.subject_packs.fixed_answer_question_builder import (
    FixedAnswerQuestion,
    to_question_card as to_fixed_answer_question_card,
)
from packages.agents.teaching_pack.subject_packs.humanities_question_builder import build_humanities_questions
from packages.agents.teaching_pack.subject_packs.language_literacy_question_builder import (
    build_language_literacy_questions,
)
from packages.agents.teaching_pack.subject_packs.math_question_builder import build_math_questions
from packages.agents.teaching_pack.subject_packs.science_question_builder import build_science_questions
from packages.agents.teaching_pack.subject_packs.solver_question_builder import (
    SolverQuestion,
    to_question_card as to_solver_question_card,
)


class NoQuizObjectivesError(ValueError):
    pass


_SubjectQuestion = SolverQuestion | FixedAnswerQuestion
_SubjectQuestionBuilder = Callable[..., list[_SubjectQuestion]]
_QuestionCardProjector = Callable[..., dict[str, Any]]
# Each subject pairs its question builder with the card projector that
# matches its question shape: solver-verified subjects (#447 Math, #448
# Science) use the arithmetic SolverQuestion shape; subjects whose
# correctness isn't solver-checkable (#449 Language and Literacy, #450
# Humanities) use the declared-answer FixedAnswerQuestion shape.
_SUBJECT_BUILDERS: dict[str, tuple[_SubjectQuestionBuilder, _QuestionCardProjector]] = {
    "math": (build_math_questions, to_solver_question_card),
    "science": (build_science_questions, to_solver_question_card),
    "language_and_literacy": (build_language_literacy_questions, to_fixed_answer_question_card),
    "humanities_and_social_studies": (build_humanities_questions, to_fixed_answer_question_card),
}


def _deterministic_seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(digest[:8], 16)


def _build_subject_quiz_questions(lesson_plan: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Real, governed questions (#447 Math, #448 Science, #449 Language and
    Literacy, #450 Humanities) when the subject has a Subject Capability
    Pack builder AND a Grade Band can be determined; falls back to the
    generic objective-matching builder (returns None) otherwise -- never
    silently mislabels an unparseable grade, or an unsupported subject, as
    governed content."""
    subject = str(lesson_plan.get("subject") or "").strip().lower()
    builder = _SUBJECT_BUILDERS.get(subject)
    if builder is None:
        return None
    build_questions, project_card = builder
    grade_level = str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or "")
    grade_band = grade_band_for_label(grade_level)
    if grade_band is None:
        return None
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "lesson")
    # instruction_language drives which locale's prompt/option text is shown
    # (falls back to the legacy generic `locale` field); target_language is
    # the separate axis of which language the taught content itself is in
    # (#449 AC: contracts/workspace keep these distinct rather than
    # conflating them into one field).
    locale = str(lesson_plan.get("instruction_language") or lesson_plan.get("locale") or "vi")
    target_language = str(lesson_plan.get("target_language") or locale)
    seed = _deterministic_seed(subject, topic, grade_band.value, target_language)
    questions = build_questions(grade_band, count=8, seed=seed, target_language=target_language)
    return [project_card(question, locale=locale) for question in questions]


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
    subject_questions = _build_subject_quiz_questions(lesson_plan)
    questions = subject_questions if subject_questions is not None else build_quiz_questions(lesson_plan)
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
