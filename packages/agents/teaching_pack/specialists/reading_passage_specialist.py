from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoGroundedPassageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReadingPassageScorecard:
    source_grounding: float
    objective_coverage: float
    question_identity: float
    answer_separation: float


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


def _grounded_source(research_brief: dict[str, Any]) -> tuple[str, str] | None:
    sources = research_brief.get("sources")
    if not isinstance(sources, list):
        return None
    for source in sources:
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            return excerpt.strip(), str(source.get("title") or source.get("url") or "Approved source")
    return None


def build_comprehension_questions(objectives: list[str]) -> list[dict[str, Any]]:
    return [{
        "id": f"passage-objective-{index}",
        "prompt": f"Which idea from the passage supports this objective? {objective}",
        "answer": objective,
        "type": "short_answer",
    } for index, objective in enumerate(objectives, start=1)]


def score_reading_passage(
    objectives: list[str],
    questions: list[dict[str, Any]],
    source_found: bool,
) -> ReadingPassageScorecard:
    ids = [str(question.get("id", "")) for question in questions]
    return ReadingPassageScorecard(
        source_grounding=1.0 if source_found else 0.0,
        objective_coverage=round(len(questions) / len(objectives), 3) if objectives else 0.0,
        question_identity=1.0 if len(ids) == len(set(ids)) else 0.0,
        answer_separation=1.0 if all(question.get("answer") for question in questions) else 0.0,
    )


def generate_reading_passage_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    source = _grounded_source(research_brief)
    if source is None:
        raise NoGroundedPassageError("no approved research excerpt to use as a reading passage")
    passage, source_ref = source
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise NoGroundedPassageError("no approved learning objectives for passage questions")
    questions = build_comprehension_questions(objectives)
    scorecard = score_reading_passage(objectives, questions, source_found=True)
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "reading_passage",
        "theme": theme,
        "title": f"Reading: {topic}",
        "sections": [{"id": "passage", "title": "Reading Passage", "content": passage}],
        "metadata": {
            "subject": str(lesson_plan.get("subject") or "General"),
            "gradeLevel": str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or ""),
            "passage_source": source_ref,
            "comprehension_questions": questions,
            "reading_passage_scorecard": {
                "source_grounding": scorecard.source_grounding,
                "objective_coverage": scorecard.objective_coverage,
                "question_identity": scorecard.question_identity,
                "answer_separation": scorecard.answer_separation,
            },
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
